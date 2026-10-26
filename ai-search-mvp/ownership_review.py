"""Preserve source authorship and saved action states; derive omissions and check drafts."""
import copy,json,hashlib
from pathlib import Path
from mcp_server import check
from retention_server import saved_notes
from retention_review import compile_review as prior_compile
ROOT=Path(__file__).resolve().parent

def digest(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def draft_hash(raw):return digest({k:v for k,v in raw.items() if k!='stop_receipt_id'})
def evidence_version(records,events):
    components=[sorted(records,key=lambda r:r['id']),saved_notes(events)]
    # Event dates, significance and dispositions are evidence too. Preserve the
    # exact legacy digest for journals that predate section extraction.
    extracted={}
    for event in events:
        if event['tool']=='save_extraction' and event['result'].get('valid'):
            for section in event['arguments']['sections']:extracted[section['section_id']]=section
    if extracted:components.append(extracted)
    return digest(components)

def compile_review(raw,records,events,draft=False):
    check(raw,json.loads((ROOT/'model/ownership.schema.json').read_text(encoding='utf-8')))
    notes=saved_notes(events);known={r['id']:r for r in records};errors=[];credits={}
    projected={k:copy.deepcopy(v) for k,v in raw.items() if k!='coverage_notes'}
    for claim in projected['claims']:
        roles=[]
        for ref in claim['roles']:
            note=notes.get(ref['record_id'],{});assertions=note.get('attributions',[]);i=ref['attribution_index']
            if not 0<=i<len(assertions):errors.append(claim['id']+': unknown saved attribution');continue
            attribution=assertions[i]
            indices=[n for n,e in enumerate(claim['evidence']) if e['record_id']==ref['record_id'] and e['span_id'] in attribution['span_ids']]
            selected={claim['evidence'][n]['span_id'] for n in indices}
            if not set(attribution['span_ids'])<=selected:errors.append(claim['id']+': attribution evidence not fully cited')
            if indices:roles.append({'actor':attribution['actor'],'role':attribution['state']+': '+attribution['action'],'evidence_indices':indices})
        claim['roles']=roles
        ids=sorted({e['record_id'] for e in claim['evidence'] if notes.get(e['record_id'],{}).get('source_kind')=='evaluation' and e['record_id'] in known})
        credits[claim['id']]=[{'record_id':id,'author':known[id]['author'],'basis':'source author metadata; not proof of sole measurement work'} for id in ids]
    used={e['record_id'] for c in projected['claims'] for e in c['evidence']}
    rejected={id for c in raw['rejected_conclusions'] for id in c['record_ids']}
    coverage={};omitted=[];partial=[]
    for note in raw['coverage_notes']:
        id=note['record_id']
        if id not in known or id in coverage or not note['reason'].strip():errors.append('Invalid coverage note: '+id)
        coverage[id]=note['reason']
        if id in used|rejected:partial.append(note|{'record_state':'represented','basis':'Coverage explanation; record is not omitted.'})
        elif notes.get(id,{}).get('relevance')=='material':omitted.append(note)
    projected['omitted_material']=omitted
    review,p=prior_compile(projected,records,events)
    if draft:
        p['errors']=[e for e in p['errors'] if e!='Missing, refused or stale completion receipt']
        p['completion_receipt_valid']=False
    else:
        matching=[e for e in events if e['tool']=='draft_check' and e['result'].get('valid') and e['result'].get('draft_hash')==draft_hash(raw) and e['result'].get('evidence_version')==evidence_version(records,events)]
        if not matching:errors.append('Final response lacks matching checked draft for current evidence')
    claims={c['id']:c for c in review['claims']};paragraphs=[]
    for id in raw['story_order']:
        if id not in claims:continue
        text=claims[id]['statement']+' '+claims[id]['limits']
        authors=sorted({c['author'] for c in credits[id]})
        if authors:text+=' Evaluation source'+('s were' if len(credits[id])>1 else ' was')+' written by '+', '.join(authors)+'.'
        paragraphs.append(text)
    review.update(account='\n\n'.join(paragraphs),source_credits=credits,coverage_notes=raw['coverage_notes'],partial_coverage_notes=partial)
    p['errors']+=errors;p['valid']=not p['errors'];p['action_states_from_saved_notes']=True;p['draft_preview']=draft;p['source_credit_records']=len({c['record_id'] for cs in credits.values() for c in cs})
    return review,p
