"""Structural evidence audit, never a semantic grade."""
import json
from pathlib import Path
from mcp_server import check
from semantic_review import validate as quote_validate
ROOT=Path(__file__).resolve().parent

def validate(review,records):
    check(review,json.loads((ROOT/'model/attribution.schema.json').read_text(encoding='utf-8')))
    result=quote_validate({k:v for k,v in review.items() if k not in {'attribution_chains','evidence_dispositions'}},records)
    errors=result['errors'];known={r['id'] for r in records};claims={c['id']:c for c in review['claims']}
    covered=set()
    for d in review['evidence_dispositions']:
        if not d['record_ids'] or not d['reason'].strip():errors.append('Empty disposition')
        for id in d['record_ids']:
            if id not in known or id in covered:errors.append('Unknown or duplicate disposition record: '+id)
            covered.add(id)
        if any(id not in claims for id in d['claim_ids']):errors.append('Unknown disposition claim')
        if d['disposition']=='used':
            cited={e['record_id'] for id in d['claim_ids'] if id in claims for e in claims[id]['evidence']}
            if not set(d['record_ids'])<=cited:errors.append('Used disposition lacks linked quotation')
    if known-covered:errors.append('Read records missing dispositions: '+', '.join(sorted(known-covered)))
    if not review['attribution_chains']:errors.append('No attribution chains')
    for chain in review['attribution_chains']:
        if not chain['intervention'].strip() or not chain['roles'] or not chain['claim_ids']:errors.append('Incomplete attribution chain')
        if any(id not in claims for id in chain['claim_ids']):errors.append('Unknown chain claim')
        cited={e['record_id'] for id in chain['claim_ids'] if id in claims for e in claims[id]['evidence']}
        for role in chain['roles']:
            if not role['actor'].strip() or not role['role'].strip() or not role['record_ids'] or not set(role['record_ids'])<=cited:errors.append('Role lacks linked source quotation')
    result['valid']=not errors
    result['disposition_records']=len(covered&known)
    result['attribution_chains']=len(review['attribution_chains'])
    result['structural_only']=True
    return result
