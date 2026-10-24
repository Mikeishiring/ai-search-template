"""Frozen-source cache, bounded earlier discovery, and a full-read index."""
import copy,json,sys
from datetime import date,timedelta,datetime,timezone
import autonomous_server as base
from followup_server import FollowupSource,TOOLS as PREVIOUS_TOOLS
from mcp_server import check

ROOT=base.ROOT
REQUEST_LIMIT=60
LOOKBACK_DAYS=90
TOOLS=copy.deepcopy(PREVIOUS_TOOLS)
for t in TOOLS:
    if t['name']=='list_roots':
        t['inputSchema']['properties']['window']['enum'].insert(0,'earlier')
        t['description']='Enumerate roots with activity in earlier [start minus 90 days,start), primary [start,end], or followup (end,horizon]. Paginated snippets; earlier history beyond the bounded sweep remains searchable and linked records remain readable.'
    if t['name']=='read_context':
        t['description']='Read one page of immediate replies. Includes the parent in full if not already read. Recursively open child contexts yourself. Exact repeated pages use saved responses without spending source budget.'
    if t['name']=='read_record':
        t['description']='Read a record in full. Previously returned full records are replayed from the frozen-source cache, with no source-budget charge. Use the full-read index to avoid unnecessary requests.'
    if t['name']=='search':
        t['description']+=' Optional window earlier restricts to dates before start, with no 90-day lower bound.'
        t['inputSchema']['properties']['window']={'type':'string','enum':['all','earlier']}

class AttributionSource(FollowupSource):
    def source_calls(self):return sum(e.get('source_charge',1) for e in self.events)
    def full_reads(self):
        return {r['id']:r for e in self.events if e['result'].get('full_records') for r in e['result'].get('items',[]) if 'parent' in r}
    def planning(self):
        p=super().planning()
        completed={(e['arguments']['source'],e['arguments']['window']) for e in self.events if e['tool']=='list_roots' and not e['arguments'].get('container') and e['result'].get('end_reached')}
        p['unfinished_window_sweeps']=[{'source':s,'window':w} for s in self.scope.get('sources',[]) for w in ['earlier','primary','followup'] if (s,w) not in completed]
        p['full_read_index']=[{k:r[k] for k in ['id','source','author','date','title']} for r in self.full_reads().values()]
        p['earlier_start']=(date.fromisoformat(self.scope['start'])-timedelta(days=LOOKBACK_DAYS)).isoformat()
        p['calls_remaining']=base.BUDGET-self.source_calls()
        p['requests_remaining']=REQUEST_LIMIT-len(self.events)
        p['attribution_review']='Before finalising, account for every fully read record: used, contextual, unresolved or irrelevant. Carry material initiators, reviewers, implementers and later owners into claims and narrative, with citations. This index does not infer roles.'
        return p
    def dispatch(self,name,args):
        if name=='list_roots' and args['window']=='earlier':
            lower=(date.fromisoformat(self.scope['start'])-timedelta(days=LOOKBACK_DAYS)).isoformat()
            rows=[r for r in self.records.values() if r['source']==args['source'] and self.accessible(r)]
            active={self.root(r)['id'] for r in rows if lower<=r['date']<self.scope['start'] and not r.get('link_only')}
            return self.page(name,args,[r for r in rows if r['id'] in active and (not args.get('container') or r['container']==args['container'])])
        if name=='search' and args.get('window')=='earlier':
            terms=args['query'].casefold().split()
            if not terms:raise ValueError('Search text required')
            return self.page(name,args,[r for r in self.records.values() if r['source']==args['source'] and self.accessible(r) and r['date']<self.scope['start'] and not r.get('link_only') and all(t in ' '.join([r['title'],r['body'],r['container']]).casefold() for t in terms)])
        result=super().dispatch(name,args)
        if name=='read_context':
            parent=self.record(args['source'],args['id'])
            if parent['id'] not in self.full_reads():
                result['items']=[parent]+result['items']
                result['included_unread_parent']=parent['id']
                result['record_metadata'].insert(0,{'id':parent['id'],'source':parent['source'],'has_children':self.snippet(parent)['has_children']})
        return result
    def cached(self,name,args):
        if name=='read_record':
            r=self.full_reads().get(args['id'])
            if r and r['source']==args['source']:
                # The metadata came from an earlier response; no hidden-corpus lookup.
                meta=next((m for e in reversed(self.events) for m in e['result'].get('record_metadata',[]) if m['id']==r['id']),None)
                return {'items':[r],'full_records':True,'record_metadata':[meta] if meta else []}
        if name in {'search','list_roots','read_context','read_attachment'}:
            e=next((e for e in self.events if e['tool']==name and e['arguments']==args and not e['result'].get('error')),None)
            if e:return {k:copy.deepcopy(v) for k,v in e['result'].items() if k not in {'planning','remaining_calls','cache_hit','source_charge'}}
        return None
    def execute(self,name,args):
        definition=next((t for t in TOOLS if t['name']==name),None)
        if not definition:raise ValueError('Tool is outside read allowlist')
        check(args,definition['inputSchema'])
        if len(self.events)>=REQUEST_LIMIT:return {'error':'request_limit_exhausted','planning':self.planning()}
        result=self.cached(name,args);hit=result is not None
        charge=0 if hit else 1
        if charge and self.source_calls()>=base.BUDGET:
            result={'error':'budget_exhausted','instruction':'Conclude with unresolved limits.'};charge=0
        elif not hit:
            try:result=self.dispatch(name,args)
            except (ValueError,KeyError,TypeError):result={'error':'invalid_or_unavailable','detail':'Check source, ID, scope or cursor.'}
        result.update(cache_hit=hit,source_charge=charge,remaining_calls=base.BUDGET-self.source_calls()-charge)
        event={'sequence':len(self.events)+1,'tool':name,'arguments':args,'result':result,'source_charge':charge,'observed_at':datetime.now(timezone.utc).isoformat()}
        self.events.append(event);result['planning']=self.planning()
        with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

if __name__=='__main__':
    folder=ROOT/'runs/attribution';folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve()
    cp=(ROOT/'fixtures/attribution.corpus.json').resolve();sp=(ROOT/'fixtures/attribution.scope.json').resolve()
    base.guard({cp,sp},log)
    server=AttributionSource(json.loads(cp.read_text(encoding='utf-8')),json.loads(sp.read_text(encoding='utf-8')),log)
    base.TOOLS=TOOLS
    for line in sys.stdin:
        try:reply=base.respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
