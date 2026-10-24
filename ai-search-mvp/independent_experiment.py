"""Separate isolated author/research invocations; immutable first outputs."""
import argparse,json,subprocess,time,hashlib,sys,re
from pathlib import Path
from model_backend import command,sha

ROOT=Path(__file__).resolve().parent
def invoke(role,prompt,instructions,schema,mcp=False,smoke=False):
    folder=ROOT/'runs'/('autonomous-smoke' if smoke else 'autonomous')/role
    folder.mkdir(parents=True,exist_ok=True)
    output=folder/'response.json'
    if output.exists() or (folder/'request.json').exists():raise RuntimeError('First attempt already exists; never silently rerun')
    (folder/'request.json').write_text(json.dumps(prompt,indent=2),encoding='utf-8')
    cmd=command(output,ROOT/schema)[:-1]
    # Override only this invocation; no persisted user configuration changes.
    cmd+=['-c','model_instructions_file='+json.dumps(str(ROOT/instructions))]
    if mcp:
        config={'command':sys.executable,'args':[str(ROOT/'autonomous_server.py')]+(['--smoke'] if smoke else []),'enabled':True,'startup_timeout_sec':30,'tool_timeout_sec':20,'enabled_tools':['source_inventory','search','list_roots','read_record','read_context','read_attachment','research_status']}
        for key,value in config.items():cmd+=['-c','mcp_servers.synthetic_research.'+key+'='+json.dumps(value)]
    started=time.monotonic()
    proc=subprocess.Popen(cmd+['-'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding='utf-8',errors='replace')
    try:stdout,stderr=proc.communicate(json.dumps(prompt),timeout=900 if mcp and not smoke else 300)
    except subprocess.TimeoutExpired:
        proc.kill();stdout,stderr=proc.communicate()
        (folder/'failure.json').write_text(json.dumps({'kind':'timeout','output_exists':output.exists()}),encoding='utf-8')
        raise RuntimeError('Transport timed out; no automatic retry')
    events=[]
    for line in stdout.splitlines():
        try:events.append(json.loads(line))
        except ValueError:pass
    completed=[e['item'] for e in events if e.get('type')=='item.completed']
    calls=[i for i in completed if i.get('type') not in {'agent_message','reasoning'}]
    unexpected=[c for c in calls if c.get('type')!='mcp_tool_call' or not mcp or c.get('server')!='synthetic_research']
    receipt={'role':role,'exit_code':proc.returncode,'elapsed_seconds':round(time.monotonic()-started,2),'provider':'Authenticated Codex CLI','model_selection':'CLI default; exact identifier not captured','prompt_sha256':sha(ROOT/instructions),'schema_sha256':sha(ROOT/schema),'request_sha256':sha(folder/'request.json'),'completed_tool_calls':len(calls),'unexpected_tool_events':len(unexpected),'usage':[e['usage'] for e in events if e.get('usage')],'isolated':True,'previous_chat_supplied':False}
    (folder/'receipt.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    (folder/'events.json').write_text(json.dumps(completed,indent=2),encoding='utf-8')
    if proc.returncode or not output.exists():
        print(json.dumps({'failed':True,'diagnostic':stderr[-1600:]}));raise RuntimeError('No complete response')
    if unexpected:raise RuntimeError('Unexpected tools: output excluded')
    print(json.dumps({'role':role,'completed':True,'seconds':receipt['elapsed_seconds'],'tool_calls':len(calls)}))

def install_story():
    # Structural validation only. Do not inspect or edit the author's story/rubric.
    folder=ROOT/'runs/autonomous'
    story=json.loads((folder/'author/response.json').read_text(encoding='utf-8'))
    corpus,scope,gold=story['corpus'],story['scope'],story['gold']
    assert corpus['synthetic'] is True and 32<=len(corpus['records'])<=40
    assert 8<=len(gold['themes'])<=12 and scope['start']<=scope['end']<=scope['horizon']
    records={r['id']:r for r in corpus['records']};assert len(records)==len(corpus['records'])
    sources={s['id'] for s in corpus['sources']};assert sources=={'chat','docs','repo'}
    for r in records.values():
        assert r['source'] in sources and r['id'].startswith(r['source']+':')
        assert re.fullmatch(r'Contributor \d{2}',r['author']) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['date'])
        assert not r['parent'] or r['parent'] in records and records[r['parent']]['source']==r['source']
        assert all(link['id'] in records and records[link['id']]['source']==link['source'] for link in r['links'])
        assert all(any(a['id']==id for a in corpus['attachments']) for id in r['attachments'])
        assert not r['repost_of'] or r['repost_of'] in records
        seen=set();p=r
        while p['parent']:
            assert p['id'] not in seen;seen.add(p['id']);p=records[p['parent']]
    assert set(gold['expected_records'])=={r['id'] for r in records.values() if r['date']<=scope['horizon']}
    assert all(t['anchors'] and all(id in gold['expected_records'] for id in t['anchors']) for t in gold['themes'])
    assert any(a['unavailable'] for a in corpus['attachments'])
    assert not re.search(r'(?i)C:[/\\]|/Users/|https?://|xox[baprs]-|sk-ant-',json.dumps(story))
    hashes={}
    for kind,obj in [('corpus',corpus),('scope',scope),('gold',gold)]:
        path=ROOT/f'fixtures/autonomous.{kind}.json'
        if path.exists():raise RuntimeError('Fixture already installed')
        path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8');hashes[kind]=sha(path)
    (folder/'story-freeze.json').write_text(json.dumps({'sha256':hashes,'structural_validation':'passed','content_edited':False,'research_started':False},indent=2),encoding='utf-8')
    print(json.dumps({'story_installed':True,'records':len(records),'themes':len(gold['themes']),'content_edited':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['author','install','smoke','research']);args=parser.parse_args()
    if args.action=='author':invoke('author',{'task':'Write an independent synthetic workplace story and its hidden evaluation rubric. You have only the author instructions and schema.'},'model/independent-author.txt','model/author.schema.json')
    elif args.action=='install':install_story()
    elif args.action=='smoke':invoke('researcher',{'task':'Connection test only. Call synthetic_research source_inventory once, then return account READY and empty claims and rejected_conclusions. Do not perform research.'},'model/autonomous-researcher.txt','model/review.schema.json',mcp=True,smoke=True)
    else:
        manifest=json.loads((ROOT/'runs/autonomous/preregistration.json').read_text(encoding='utf-8'))
        for name,expected in manifest['freeze'].items():assert sha(ROOT/name)==expected,('Changed preregistered file',name)
        freeze=json.loads((ROOT/'runs/autonomous/story-freeze.json').read_text(encoding='utf-8'))
        for kind,expected in freeze['sha256'].items():assert sha(ROOT/f'fixtures/autonomous.{kind}.json')==expected
        scope=json.loads((ROOT/'fixtures/autonomous.scope.json').read_text(encoding='utf-8'))
        invoke('researcher',{'synthetic':True,'scope':scope,'task':'Investigate the question using your own follow-up choices. No evidence packet or answer key is supplied. Use only the synthetic_research MCP. Return the required evidence account when finished.'},'model/autonomous-researcher.txt','model/review.schema.json',mcp=True)
