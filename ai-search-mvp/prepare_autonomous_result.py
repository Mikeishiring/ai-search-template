"""Audit only after research ends. Never feeds newly found evidence back to the model."""
import json,hashlib
from pathlib import Path
from semantic_review import validate
from reviewer import inspect,components
ROOT=Path(__file__).resolve().parent
folder=ROOT/'runs/autonomous'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
review=read(folder/'researcher/response.json')
receipt=read(folder/'researcher/receipt.json')
assert receipt['exit_code']==0 and receipt['unexpected_tool_events']==0
events=[json.loads(line) for line in (folder/'calls.jsonl').read_text(encoding='utf-8').splitlines()]
corpus=read(ROOT/'fixtures/autonomous.corpus.json');scope=read(ROOT/'fixtures/autonomous.scope.json')
freeze=read(folder/'story-freeze.json');preregister=read(folder/'preregistration.json')
for kind,sha in freeze['sha256'].items():assert hashlib.sha256((ROOT/f'fixtures/autonomous.{kind}.json').read_bytes()).hexdigest()==sha
for file,sha in preregister['freeze'].items():assert hashlib.sha256((ROOT/file).read_bytes()).hexdigest()==sha
full={};snippets=set()
for event in events:
    for r in event['result'].get('items',[]):
        if 'parent' in r and 'source' in r:
            if event['result'].get('full_records'):full[r['id']]=r
            else:snippets.add(r['id'])
records=sorted(full.values(),key=lambda r:(r['date'],r['id']))
accessible=[r for r in corpus['records'] if r['date']<=scope['horizon']]
assert all(r in corpus['records'] for r in records)
provenance=validate(review,records)
(folder/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
audit=[r for r in accessible if r['id'] not in full]
(folder/'audit-records.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
pending={}
for event in events:
    result=event['result'];args=event['arguments'];signature=json.dumps([event['tool'],{k:v for k,v in args.items() if k!='cursor'}],sort_keys=True)
    if 'next_cursor' in result:
        if result['next_cursor']:pending[signature]={'tool':event['tool'],'arguments':args,'next_cursor':result['next_cursor']}
        else:pending.pop(signature,None)
coverage=[]
for source in corpus['sources']:
    source_id=source['id']
    enumeration=[e for e in events if e['tool']=='list_roots' and e['arguments'].get('source')==source_id and not e['arguments'].get('container')]
    coverage.append({'source':source_id,'platform':source['platform'],'records_retrieved':sum(r['source']==source_id for r in records),'expected_records':sum(r['source']==source_id for r in accessible),'snippet_only':sum(r['source']==source_id and r['id'] in snippets and r['id'] not in full for r in accessible),'enumeration_end':any(e['result'].get('end_reached') for e in enumeration),'blocked':sum(bool(e['arguments'].get('source')==source_id and (e['result'].get('unavailable') or e['result'].get('error'))) for e in events),'pending':sum(x['arguments'].get('source')==source_id for x in pending.values())})
result={'synthetic':True,'scope':scope,'status':'first_model_attempt_complete','records':records,'findings':[f for r in records for f in inspect(r)],'components':components(records),'coverage':coverage,'tasks':[],'receipts':len(events),'input_files':['fixtures/autonomous.scope.json','MCP responses recorded in runs/autonomous/calls.jsonl']}
(folder/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
trace={'events':events,'source_calls':len(events),'budget':preregister['source_call_budget'],'searches':sum(e['tool']=='search' for e in events),'full_records':len(records),'snippet_only_ids':sorted(snippets-set(full)),'not_fully_read_ids':[r['id'] for r in audit],'pending_pages':list(pending.values()),'unknowns':review['unknowns'],'source_coverage':coverage,'full_read_inventory_scope':'All accessible records through the horizon, including distractors; relevance is scored separately against the author rubric.'}
(folder/'trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
print(json.dumps({'source_calls':len(events),'full_records':len(records),'accessible_records':len(accessible),'not_fully_read':len(audit),'quote_count':provenance['quote_count'],'quote_validation':provenance['valid'],'quote_errors':provenance['errors'],'pending_pages':len(pending)}))
