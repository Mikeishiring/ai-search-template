"""Observed branch priorities and subject-authored audit index; no automatic reads."""
import json,sys
import autonomous_server as base
from completion_server import CompletionSource,TOOLS
ROOT=base.ROOT

class DepthSource(CompletionSource):
    def planning(self):
        p=super().planning();observed={}
        for event in self.events:
            for r in event['result'].get('items',[]):
                if 'parent' in r:observed[r['id']]=r
        def depth(id):
            seen=set();n=0
            while id in observed and observed[id].get('parent') and id not in seen:
                seen.add(id);id=observed[id]['parent'];n+=1
            return n
        branches=[]
        for lead in p['unopened_contexts']:
            if lead['root_read']:
                branches.append({'tool':'read_context','arguments':{'source':lead['source'],'id':lead['id']},'observed_depth':depth(lead['id'])})
        for page in p['pending_pages']:
            if page['tool']=='read_context':
                branches=[b for b in branches if b['arguments']['id']!=page['arguments']['id']]
                branches.append(page|{'observed_depth':depth(page['arguments']['id'])})
        p['priority_branches']=sorted(branches,key=lambda b:(-b['observed_depth'],b['arguments']['id']))
        p['subject_authored_full_records']=[{'id':r['id'],'title':r['title'],'date':r['date']} for r in self.full_reads().values() if r['author']==self.scope.get('subject')]
        p['priority_policy']='Close already-open branches, deepest first, before unrelated standalone reads. This is an observed structural recommendation, not a relevance score. Preserve later-window discovery budget; explain deviations in final research_choices.'
        return p

if __name__=='__main__':
    folder=ROOT/'runs/depth';folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve();cp=(ROOT/'fixtures/depth.corpus.json').resolve();sp=(ROOT/'fixtures/depth.scope.json').resolve()
    base.guard({cp,sp},log)
    server=DepthSource(json.loads(cp.read_text(encoding='utf-8')),json.loads(sp.read_text(encoding='utf-8')),log);base.TOOLS=TOOLS
    for line in sys.stdin:
        try:reply=base.respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
