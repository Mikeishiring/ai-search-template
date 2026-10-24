"""Validate model provenance without pretending to validate the meaning."""
import json
from pathlib import Path
from adapter import digest
from mcp_server import check

ROOT=Path(__file__).resolve().parent


def validate(review, records):
    schema=json.loads((ROOT/'model/review.schema.json').read_text(encoding='utf-8'))
    check(review,schema)
    mapping={r['id']:r for r in records}
    ids=set()
    anchored=[]
    errors=[]
    for claim in review['claims']:
        if not claim['id'].strip() or claim['id'] in ids:
            errors.append('Empty or duplicate claim ID')
        ids.add(claim['id'])
        if not claim['statement'].strip() or not claim['evidence']:
            errors.append(f"{claim['id']}: claim or evidence missing")
        anchors=[]
        for evidence in claim['evidence']:
            record=mapping.get(evidence['record_id'])
            quote=evidence['quote']
            if not record or not quote or record['body'].count(quote)!=1:
                errors.append(f"{claim['id']}: quote missing or ambiguous in {evidence['record_id']}")
                continue
            start=record['body'].index(quote)
            anchors.append(dict(evidence,start=start,end=start+len(quote),record_hash=digest(record)))
        anchored.append(dict(claim,evidence=anchors,state='needs_semantic_assessment'))
    for rejection in review['rejected_conclusions']:
        if not rejection['record_ids'] or any(id not in mapping for id in rejection['record_ids']):
            errors.append('Rejected conclusion lacks valid source IDs')
    return {'valid':not errors,'errors':errors,'claims':anchored,
            'quote_count':sum(len(c['evidence']) for c in anchored),
            'meaning_validated':False}


if __name__=='__main__':
    folder=ROOT/'runs/semantic'
    review=json.loads((folder/'model/review.json').read_text(encoding='utf-8'))
    records=json.loads((folder/'result.json').read_text(encoding='utf-8'))['records']
    result=validate(review,records)
    (folder/'model/provenance.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['valid','errors','quote_count','meaning_validated']}))
