"""Observed-record completion gate and immutable source-span citations."""
import copy,hashlib,json,re,sys
from datetime import datetime,timezone
import autonomous_server as base
from attribution_server import AttributionSource,TOOLS as PRIOR_TOOLS
from mcp_server import check
ROOT=base.ROOT
REQUEST_LIMIT=80
TOOLS=copy.deepcopy(PRIOR_TOOLS)+[base.tool('finish_check','Check whether stopping is justified from receipts. Free local audit. Refuses a completion receipt while actionable observed records or discovery work remain and budget is available. Returns authoritative counts and unresolved leads; never certifies unseen archive coverage.',{},[])]

def spans(record):
    text=record['body'];revision=hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]
    boundaries=[0]+[m.end() for m in re.finditer(r'(?<=[.!?])\s+',text)]+[len(text)]
    result=[]
    for start,end in zip(boundaries,boundaries[1:]):
        while end>start and text[end-1].isspace():end-=1
        if end>start:result.append({'record_id':record['id'],'span_id':record['id']+':'+revision+':'+str(start),'start':start,'end':end,'quote':text[start:end]})
    return result

class CompletionSource(AttributionSource):
    def planning(self):
        p=super().planning();full=self.full_reads();seen={}
        for e in self.events:
            for r in e['result'].get('items',[]):
                if 'parent' in r:seen[r['id']]=r
        p['unread_surfaced_records']=[{k:r[k] for k in ['id','source','title','date']} for id,r in sorted(seen.items()) if id not in full]
        p['requests_remaining']=REQUEST_LIMIT-len(self.events)
        p['stop_policy']='Read surfaced records before dismissing relevance. finish_check is required before the final response; do not invent a budget explanation.'
        return p
    def decorate(self,result):
        if result.get('full_records'):result['citation_spans']=[s for r in result['items'] for s in spans(r)]
        return result
    def finish(self):
        p=self.planning()
        keys=['unread_surfaced_records','unopened_contexts','unread_references','unchecked_attachments','pending_pages','unfinished_window_sweeps']
        unresolved={k:p[k] for k in keys}
        pending=any(unresolved.values())
        source_limit=self.source_calls()>=base.BUDGET
        request_limit=len(self.events)+1>=REQUEST_LIMIT
        allowed=not pending or source_limit or request_limit
        status='source_limit' if source_limit and pending else 'request_limit' if request_limit and pending else 'observed_scope_complete' if not pending else 'continue_research'
        counts={'source_calls':self.source_calls(),'source_budget':base.BUDGET,'requests_including_this_check':len(self.events)+1,'request_limit':REQUEST_LIMIT,'source_calls_remaining':base.BUDGET-self.source_calls(),'requests_remaining':REQUEST_LIMIT-len(self.events)-1}
        receipt={'allowed':allowed,'status':status,'counts':counts,'unresolved':unresolved,'scope':'Observed records and enumerated windows only; unseen source contents and semantic completeness are not certified.'}
        receipt['receipt_id']=base.digest([receipt,[(e['sequence'],e['tool'],e['arguments']) for e in self.events]]) if allowed else None
        return receipt
    def execute(self,name,args):
        definition=next((t for t in TOOLS if t['name']==name),None)
        if not definition:raise ValueError('Tool is outside read allowlist')
        check(args,definition['inputSchema'])
        if len(self.events)>=REQUEST_LIMIT:return {'error':'request_limit_exhausted','planning':self.planning()}
        local=name in {'finish_check','research_status'}
        result=None if local else self.cached(name,args);hit=result is not None
        charge=0 if hit or local else 1
        if name=='finish_check':result=self.finish()
        elif name=='research_status':result={'counts':{'source_calls':self.source_calls(),'requests_before_this_check':len(self.events)},'full_record_ids':sorted(self.full_reads())}
        elif charge and self.source_calls()>=base.BUDGET:result={'error':'budget_exhausted','instruction':'Call finish_check and report its actual unresolved limits.'};charge=0
        elif not hit:
            try:result=self.dispatch(name,args)
            except (ValueError,KeyError,TypeError):result={'error':'invalid_or_unavailable','detail':'Check source, ID, scope or cursor.'}
        self.decorate(result)
        result.update(cache_hit=hit,source_charge=charge,remaining_calls=base.BUDGET-self.source_calls()-charge)
        event={'sequence':len(self.events)+1,'tool':name,'arguments':args,'result':result,'source_charge':charge,'observed_at':datetime.now(timezone.utc).isoformat()}
        self.events.append(event);result['planning']=self.planning()
        with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

if __name__=='__main__':
    folder=ROOT/'runs/completion';folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve();cp=(ROOT/'fixtures/completion.corpus.json').resolve();sp=(ROOT/'fixtures/completion.scope.json').resolve()
    base.guard({cp,sp},log)
    server=CompletionSource(json.loads(cp.read_text(encoding='utf-8')),json.loads(sp.read_text(encoding='utf-8')),log);base.TOOLS=TOOLS
    for line in sys.stdin:
        try:reply=base.respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
