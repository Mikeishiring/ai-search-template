"""Resolve immutable span IDs; validate completion receipts without semantic grading."""
import copy,json
from pathlib import Path
from mcp_server import check
from completion_server import spans
from attribution_review import validate as attribution_validate
ROOT=Path(__file__).resolve().parent

def compile_review(raw,records,events):
    check(raw,json.loads((ROOT/'model/completion.schema.json').read_text(encoding='utf-8')))
    catalog={s['span_id']:s for r in records for s in spans(r)}
    review={k:copy.deepcopy(v) for k,v in raw.items() if k not in {'stop_receipt_id','attachment_dispositions'}}
    errors=[];anchored=[]
    for claim in review['claims']:
        evidence=[];anchors=[]
        for ref in claim['evidence']:
            span=catalog.get(ref['span_id'])
            if span is None or span['record_id']!=ref['record_id']:
                errors.append(claim['id']+': unknown or mismatched source span '+ref['span_id'])
                evidence.append({'record_id':ref['record_id'],'quote':''})
            else:
                evidence.append({'record_id':span['record_id'],'quote':span['quote']});anchors.append(span)
        claim['evidence']=evidence
        anchored.append(dict(claim,evidence=anchors,state='needs_semantic_assessment'))
    provenance=attribution_validate(review,records)
    # Source offsets disambiguate identical sentences; older text-only validation cannot.
    provenance['errors']=[e for e in provenance['errors'] if 'quote missing or ambiguous' not in e]+errors
    provenance['claims']=anchored;provenance['quote_count']=sum(len(c['evidence']) for c in anchored)
    checked={e['arguments']['id'] for e in events if e['tool']=='read_attachment' and not e['result'].get('error')}
    covered=set();claim_ids={c['id'] for c in review['claims']}
    for d in raw['attachment_dispositions']:
        if d['attachment_id'] not in checked or d['attachment_id'] in covered:provenance['errors'].append('Unobserved or duplicate attachment disposition')
        if not d['reason'].strip() or any(id not in claim_ids for id in d['claim_ids']):provenance['errors'].append('Invalid attachment disposition reason or claim')
        covered.add(d['attachment_id'])
    if checked-covered:provenance['errors'].append('Checked attachments missing dispositions')
    final=events[-1] if events else {}
    receipt=final.get('result',{}) if final.get('tool')=='finish_check' else {}
    valid_stop=bool(receipt.get('allowed') and receipt.get('receipt_id')==raw['stop_receipt_id'])
    if not valid_stop:provenance['errors'].append('Missing, refused or stale completion receipt')
    provenance.update(valid=not provenance['errors'],completion_receipt_valid=valid_stop,attachment_dispositions=len(covered&checked),span_resolution=True,meaning_validated=False)
    review.update(stop_receipt_id=raw['stop_receipt_id'],attachment_dispositions=raw['attachment_dispositions'])
    return review,provenance
