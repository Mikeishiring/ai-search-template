"""Compile narrative from supported claim sentences; reconcile read and rejected evidence."""
import copy,json
from pathlib import Path
from mcp_server import check
from retention_server import saved_notes
from depth_review import compile_review as depth_compile
ROOT=Path(__file__).resolve().parent

def compile_review(raw,records,events):
    check(raw,json.loads((ROOT/'model/retention.schema.json').read_text(encoding='utf-8')))
    notes=saved_notes(events);known={r['id'] for r in records};errors=[]
    claims={c['id']:c for c in raw['claims']};order=raw['story_order']
    if len(order)!=len(set(order)) or set(order)!=set(claims):errors.append('Story order must include every claim exactly once')
    account='\n\n'.join(claims[id]['statement']+' '+claims[id]['limits'] for id in order if id in claims)
    used={e['record_id'] for c in raw['claims'] for e in c['evidence']}
    rejections={}
    for rejection in raw['rejected_conclusions']:
        for id in rejection['record_ids']:rejections.setdefault(id,[]).append(rejection['reason'])
    omissions={}
    for omission in raw['omitted_material']:
        id=omission['record_id']
        if id in omissions or id in used or id in rejections or notes.get(id,{}).get('relevance')!='material' or not omission['reason'].strip():
            errors.append('Invalid material omission: '+id)
        omissions[id]=omission['reason']
    uncited=[]
    for id in sorted(known):
        note=notes.get(id)
        if not note:errors.append('Read record lacks persistent note: '+id)
        if id in used:continue
        if id in rejections:reason='Supports rejected conclusion: '+' '.join(rejections[id]);disposition='contextual'
        elif note and note['relevance']=='material':
            reason=omissions.get(id,'Material finding was dropped without explanation.');disposition='unresolved'
            if id not in omissions:errors.append('Material finding missing from claims or explicit omissions: '+id)
        else:
            reason=note['finding'] if note else 'No persistent note supplied.'
            disposition=note['relevance'] if note else 'unresolved'
        uncited.append({'record_id':id,'disposition':disposition,'reason':reason})
    projected={k:copy.deepcopy(raw[k]) for k in ['claims','unknowns','rejected_conclusions','stop_receipt_id','research_choices']}
    projected.update(account=account,uncited_records=uncited)
    review,p=depth_compile(projected,records,events)
    p['errors']+=errors;p['valid']=not p['errors'];p['narrative_compiled']=True
    p['rejection_only_records']=sorted(set(rejections)&known-used)
    p['material_notes']=sum(n['relevance']=='material' for n in notes.values())
    p['material_notes_represented']=sum(n['relevance']=='material' and id in used|set(rejections) for id,n in notes.items())
    review.update(story_order=order,evidence_notes=list(notes.values()),omitted_material=raw['omitted_material'])
    return review,p
