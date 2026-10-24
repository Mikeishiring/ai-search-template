"""Derive evidence relationships; preserve semantic decisions and reject missing ones."""
import copy,json
from pathlib import Path
from mcp_server import check
from completion_server import spans
from completion_review import compile_review as prior_compile
ROOT=Path(__file__).resolve().parent

def compile_review(raw,records,events):
    check(raw,json.loads((ROOT/'model/depth.schema.json').read_text(encoding='utf-8')))
    projected={k:copy.deepcopy(raw[k]) for k in ['account','claims','unknowns','rejected_conclusions','stop_receipt_id']}
    catalog={s['span_id']:s for r in records for s in spans(r)};errors=[];chains=[];used={}
    ids=[c['id'] for c in raw['claims']]
    if len(ids)!=len(set(ids)):errors.append('Duplicate claim ID')
    for claim,out in zip(raw['claims'],projected['claims']):
        out.pop('roles');roles=[]
        validrefs=[e for e in claim['evidence'] if e['span_id'] in catalog and catalog[e['span_id']]['record_id']==e['record_id']]
        for ref in validrefs:used.setdefault(ref['record_id'],set()).add(claim['id'])
        for role in claim['roles']:
            evidence=[]
            for i in role['evidence_indices']:
                if type(i)!=int or not 0<=i<len(claim['evidence']):errors.append(claim['id']+': invalid role evidence index');continue
                ref=claim['evidence'][i]
                if ref not in validrefs:errors.append(claim['id']+': role cites invalid source span');continue
                evidence.append(ref['record_id'])
            if not evidence:errors.append(claim['id']+': role has no source support')
            roles.append({'actor':role['actor'],'role':role['role'],'record_ids':sorted(set(evidence))})
        if roles:chains.append({'intervention':claim['statement'],'roles':roles,'claim_ids':[claim['id']],'limits':claim['limits']})
    known={r['id'] for r in records};notes={}
    for d in raw['uncited_records']:
        id=d['record_id']
        if id not in known or id in notes or id in used:errors.append('Invalid, duplicate or already cited omission: '+id)
        if not d['reason'].strip():errors.append('Empty omission reason: '+id)
        notes[id]=d
    dispositions=[]
    for id in sorted(known):
        if id in used:dispositions.append({'record_ids':[id],'disposition':'used','claim_ids':sorted(used[id]),'reason':'Derived from selected source spans.'})
        elif id in notes:dispositions.append({'record_ids':[id],'disposition':notes[id]['disposition'],'claim_ids':[],'reason':notes[id]['reason']})
        else:
            errors.append('Read record lacks citation or omission explanation: '+id)
            dispositions.append({'record_ids':[id],'disposition':'unresolved','claim_ids':[],'reason':'Model omitted the required explanation; unresolved by compiler.'})
    attachments={}
    for e in events:
        if e['tool']=='read_attachment' and not e['result'].get('error'):
            attachments[e['arguments']['id']]={'attachment_id':e['arguments']['id'],'reason':'Unavailable source (receipt).' if e['result'].get('unavailable') else 'Attachment returned by source; not proof of adoption.','claim_ids':[]}
    projected.update(attribution_chains=chains,evidence_dispositions=dispositions,attachment_dispositions=list(attachments.values()))
    review,provenance=prior_compile(projected,records,events)
    provenance['errors']+=errors;provenance['valid']=not provenance['errors'];provenance['bookkeeping_derived']=True
    review['research_choices']=raw['research_choices']
    return review,provenance
