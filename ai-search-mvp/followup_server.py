"""Observed-evidence planning ledger; no gold, automatic reads or semantic hints."""
import copy,json,sys
from datetime import datetime,timezone
import autonomous_server as base
from mcp_server import check

ROOT=base.ROOT
TOOLS=copy.deepcopy(base.TOOLS)
for definition in TOOLS:
    if definition['name']=='list_roots':
        definition['inputSchema']['properties']['window']={'type':'string','enum':['primary','followup']}
        definition['inputSchema']['required'].append('window')
        definition['description']='Enumerate roots with activity in primary [start,end] or followup (end,horizon] window. Includes older roots with replies in that window. Paginated snippets, not full reads.'
    if definition['name']=='research_status':
        definition['description']='Inspect observed unread replies, references, attachments, pagination and unfinished window sweeps. Obligations are discovery leads, not proof of relevance or adoption.'

class FollowupSource(base.ResearchSource):
    def planning(self):
        # Build hints ONLY from returned evidence/metadata and the declared scope.
        observed={};full=set();contexts=set();references={};attachments={};attempted=set();pending={};sweeps=set()
        for e in self.events:
            result,args,name=e['result'],e['arguments'],e['tool']
            if result.get('error'):continue
            for r in result.get('items',[]):
                if 'parent' not in r:continue
                observed[r['id']]=observed.get(r['id'],{})|r
                if result.get('full_records'):
                    full.add(r['id'])
                    for ref in r.get('links',[]):references[ref['id']]=ref['source']
                    if r.get('parent'):references[r['parent']]=r['source']
                    for aid in r.get('attachments',[]):attachments[aid]=r['source']
            for meta in result.get('record_metadata',[]):
                observed[meta['id']]=observed.get(meta['id'],{})|meta
            signature=base.digest([name,{k:v for k,v in args.items() if k!='cursor'}])
            if 'next_cursor' in result:
                if result['next_cursor']:
                    pending[signature]={'tool':name,'arguments':{**args,'cursor':result['next_cursor']}}
                else:pending.pop(signature,None)
            if name=='read_context' and result.get('end_reached'):contexts.add(args['id'])
            if name=='read_attachment':attempted.add(args['id'])
            if name=='list_roots' and not args.get('container') and result.get('end_reached'):
                sweeps.add((args['source'],args['window']))
        return {
            'unopened_contexts':[{'source':r['source'],'id':id,'root_read':id in full} for id,r in sorted(observed.items()) if r.get('has_children') and id not in contexts],
            'unread_references':[{'source':source,'id':id} for id,source in sorted(references.items()) if id not in full],
            'unchecked_attachments':[{'source':source,'id':id} for id,source in sorted(attachments.items()) if id not in attempted],
            'pending_pages':list(pending.values()),
            'unfinished_window_sweeps':[{'source':source,'window':window} for source in self.scope.get('sources',[]) for window in ['primary','followup'] if (source,window) not in sweeps],
            'later_use':'A completed sweep is discovery coverage, not proof of continued use. Read the relevant later evidence and separate reports from measurement.',
            'calls_remaining':base.BUDGET-len(self.events),
            'scope':'Known leads only; no unseen content or hidden rubric consulted.'}

    def dispatch(self,name,args):
        if name=='list_roots':
            rows=[r for r in self.records.values() if r['source']==args['source'] and self.accessible(r)]
            def in_window(r):
                return self.scope['start']<=r['date']<=self.scope['end'] if args['window']=='primary' else self.scope['end']<r['date']<=self.scope['horizon']
            active={self.root(r)['id'] for r in rows if in_window(r) and not r.get('link_only')}
            result=self.page(name,args,[r for r in rows if r['id'] in active and (not args.get('container') or r['container']==args['container'])])
        else:result=super().dispatch(name,args)
        if result.get('full_records'):
            result['record_metadata']=[{'id':r['id'],'source':r['source'],'has_children':self.snippet(r)['has_children']} for r in result['items']]
        return result

    def execute(self,name,args):
        definition=next((t for t in TOOLS if t['name']==name),None)
        if not definition:raise ValueError('Tool is outside read allowlist')
        check(args,definition['inputSchema'])
        if len(self.events)>=base.BUDGET:return {'error':'budget_exhausted','remaining_calls':0,'planning':self.planning()}
        try:result=self.dispatch(name,args)
        except (ValueError,KeyError,TypeError):result={'error':'invalid_or_unavailable','detail':'Check source, ID, scope or cursor.'}
        result['remaining_calls']=base.BUDGET-len(self.events)-1
        event={'sequence':len(self.events)+1,'tool':name,'arguments':args,'result':result,'observed_at':datetime.now(timezone.utc).isoformat()}
        self.events.append(event)
        result['planning']=self.planning()
        with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

if __name__=='__main__':
    folder=ROOT/'runs/followup';folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve()
    cp=(ROOT/'fixtures/followup.corpus.json').resolve();sp=(ROOT/'fixtures/followup.scope.json').resolve()
    base.guard({cp,sp},log)
    server=FollowupSource(json.loads(cp.read_text(encoding='utf-8')),json.loads(sp.read_text(encoding='utf-8')),log)
    base.TOOLS=TOOLS
    for line in sys.stdin:
        try:reply=base.respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
