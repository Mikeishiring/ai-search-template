"""Read-only synthetic MCP. No automatic research, arbitrary file input, or answer key."""
import hashlib,json,sys,os
from pathlib import Path
from datetime import datetime,timezone
from mcp_server import check

ROOT=Path(__file__).resolve().parent
BUDGET=45
PAGE_SIZE=3
S={'type':'string'}
SOURCE={'type':'string','enum':['chat','docs','repo']}
def tool(name,description,properties,required):
    return {'name':name,'description':description,'inputSchema':{'type':'object','properties':properties,'required':required,'additionalProperties':False},'annotations':{'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False}}
TOOLS=[
 tool('source_inventory','Describe the synthetic sources, containers, scope and read capabilities. Does not enumerate every record.',{},[]),
 tool('search','Search a source through the follow-up horizon. All whitespace-separated terms must match title/body/container; case-insensitive, no query operators. Returns paginated snippets, not full reads.',{'source':SOURCE,'query':S,'cursor':S},['source','query']),
 tool('list_roots','Enumerate roots with activity in the question window, including older roots with later replies. Optional container filter. Returns metadata/snippets; expand threads and nested blocks separately.',{'source':SOURCE,'container':S,'cursor':S},['source']),
 tool('read_record','Read one complete original record by ID. Later-than-horizon records are unavailable.',{'source':SOURCE,'id':S},['source','id']),
 tool('read_context','Read one page of immediate replies or nested blocks under a record. Follow returned child IDs to expand deeper nesting. Does not automatically read links or grandchildren.',{'source':SOURCE,'id':S,'cursor':S},['source','id']),
 tool('read_attachment','Read a referenced attachment or receive an explicit unavailable result.',{'source':SOURCE,'id':S},['source','id']),
 tool('research_status','Inspect tool receipts: full records read, snippet-only records seen and remaining budget. This does not claim complete source coverage.',{},[])
]
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

class ResearchSource:
    def __init__(self,corpus,scope,log_path):
        if corpus.get('synthetic') is not True:raise ValueError('Synthetic corpus required')
        self.corpus,self.scope,self.path=corpus,scope,log_path
        self.records={r['id']:r for r in corpus['records']}
        self.events=[json.loads(line) for line in log_path.read_text(encoding='utf-8').splitlines()] if log_path.exists() else []
    def accessible(self,r):return r['date']<=self.scope['horizon']
    def record(self,source,id):
        r=self.records.get(id)
        if not r or r['source']!=source or not self.accessible(r):raise ValueError('Record unavailable within scope')
        return r
    def root(self,r):
        seen=set()
        while r['parent']:
            if r['id'] in seen:raise ValueError('Parent cycle')
            seen.add(r['id']);r=self.records[r['parent']]
        return r
    def snippet(self,r):return {key:r[key] for key in ['id','source','date','author','container','title','parent']}|{'snippet':r['body'][:160],'has_children':any(x['parent']==r['id'] and self.accessible(x) for x in self.records.values())}
    def page(self,name,args,rows,full=False):
        rows=sorted(rows,key=lambda r:(r['date'],r['id']))
        identity=digest([name,{k:v for k,v in args.items() if k!='cursor'}])[:12]
        offset=0
        if args.get('cursor'):
            prefix,n=args['cursor'].split(':')
            if prefix!=identity or not n.isdigit():raise ValueError('Cursor does not match this query')
            offset=int(n)
        batch=rows[offset:offset+PAGE_SIZE]
        more=offset+len(batch)<len(rows)
        return {'items':batch if full else [self.snippet(r) for r in batch],'full_records':full,'next_cursor':f'{identity}:{offset+len(batch)}' if more else None,'page_size':PAGE_SIZE,'end_reached':not more,'returned_count':len(batch)}
    def status(self):
        full=set();seen=set()
        for e in self.events:
            for r in e['result'].get('items',[]):
                if r.get('id') in self.records:
                    seen.add(r['id'])
                    if e['result'].get('full_records'):full.add(r['id'])
        return {'full_record_ids':sorted(full),'snippet_only_ids':sorted(seen-full),'source_coverage':'not certified','calls_used':len(self.events)}
    def dispatch(self,name,args):
        if name=='source_inventory':
            return {'synthetic':True,'scope':self.scope,'sources':[s|{'containers':sorted({r['container'] for r in self.records.values() if r['source']==s['id'] and self.accessible(r)})} for s in self.corpus['sources']],'capabilities':'Explicit search, root enumeration, record, immediate-context and attachment reads. No automatic traversal. Snippets are not full reads.'}
        if name=='research_status':return self.status()
        source=args['source']
        rows=[r for r in self.records.values() if r['source']==source and self.accessible(r)]
        if name=='search':
            terms=args['query'].casefold().split()
            if not terms:raise ValueError('Search text required')
            rows=[r for r in rows if not r.get('link_only') and all(t in ' '.join([r['title'],r['body'],r['container']]).casefold() for t in terms)]
            return self.page(name,args,rows)
        if name=='list_roots':
            active={self.root(r)['id'] for r in rows if self.scope['start']<=r['date']<=self.scope['end'] and not r.get('link_only')}
            return self.page(name,args,[r for r in rows if r['id'] in active and (not args.get('container') or r['container']==args['container'])])
        if name=='read_record':return {'items':[self.record(source,args['id'])],'full_records':True}
        if name=='read_context':
            self.record(source,args['id'])
            return self.page(name,args,[r for r in rows if r['parent']==args['id']],full=True)
        if name=='read_attachment':
            attachment=next((a for a in self.corpus['attachments'] if a['id']==args['id'] and a['source']==source),None)
            if not attachment or attachment['unavailable']:return {'items':[],'unavailable':True,'reason':'Original attachment unavailable; not evidence of approval or failure.'}
            return {'items':[attachment],'full_records':False,'attachment':True}
        raise ValueError('Unknown tool')
    def execute(self,name,args):
        definition=next((t for t in TOOLS if t['name']==name),None)
        if not definition:raise ValueError('Tool is outside read allowlist')
        check(args,definition['inputSchema'])
        if len(self.events)>=BUDGET:return {'error':'budget_exhausted','remaining_calls':0,'instruction':'Return your account with the unresolved limits.'}
        try:result=self.dispatch(name,args)
        except (ValueError,KeyError,TypeError):result={'error':'invalid_or_unavailable','detail':'Check source, ID, scope or cursor. No private files are accessible.'}
        result['remaining_calls']=BUDGET-len(self.events)-1
        event={'sequence':len(self.events)+1,'tool':name,'arguments':args,'result':result,'observed_at':datetime.now(timezone.utc).isoformat()}
        self.events.append(event)
        with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

def respond(message,server):
    if 'id' not in message:return None
    id=message['id'];method=message.get('method')
    if method=='initialize':result={'protocolVersion':'2025-06-18','capabilities':{'tools':{}},'serverInfo':{'name':'synthetic_research','version':'0.2.0'}}
    elif method=='ping':result={}
    elif method=='tools/list':result={'tools':TOOLS}
    elif method=='tools/call':
        try:
            p=message['params'];data=server.execute(p['name'],p.get('arguments',{}))
            result={'content':[{'type':'text','text':json.dumps(data,ensure_ascii=False)}],'isError':'error' in data}
        except (KeyError,ValueError,TypeError):result={'content':[{'type':'text','text':'Request rejected: invalid tool or arguments.'}],'isError':True}
    else:return {'jsonrpc':'2.0','id':id,'error':{'code':-32601,'message':'Method not found'}}
    return {'jsonrpc':'2.0','id':id,'result':result}

def guard(allowed_reads,log):
    def audit(event,args):
        if event in {'socket.connect','socket.bind','socket.getaddrinfo','subprocess.Popen','os.system'}:raise PermissionError('Offline source boundary')
        if event!='open' or not isinstance(args[0],(str,bytes,os.PathLike)):return
        path=Path(os.fsdecode(args[0])).resolve()
        if path not in allowed_reads|{log}:raise PermissionError('File outside fixed synthetic source boundary')
        mode=args[1] or ''
        if path!=log and any(c in str(mode) for c in 'wax+'):raise PermissionError('Source is read only')
    sys.addaudithook(audit)

if __name__=='__main__':
    smoke=sys.argv[1:]==['--smoke']
    folder=ROOT/'runs'/('autonomous-smoke' if smoke else 'autonomous')
    folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve()
    cp=(ROOT/'fixtures/autonomous.corpus.json').resolve();sp=(ROOT/'fixtures/autonomous.scope.json').resolve()
    guard({cp,sp},log)
    if smoke:
        corpus={'synthetic':True,'sources':[{'id':'chat','platform':'Smoke only','enumeration':True}],'records':[],'attachments':[]}
        scope={'question':'Connection smoke test','start':'2040-01-01','end':'2040-01-31','horizon':'2040-02-28','sources':['chat']}
    else:corpus=json.loads(cp.read_text(encoding='utf-8'));scope=json.loads(sp.read_text(encoding='utf-8'))
    server=ResearchSource(corpus,scope,log)
    for line in sys.stdin:
        try:reply=respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
