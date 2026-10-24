"""Cache-only writing recovery and persistent per-record notes. Synthetic inputs only."""
import copy,json,sys
from datetime import datetime,timezone
import autonomous_server as base
from completion_server import TOOLS as PRIOR_TOOLS,REQUEST_LIMIT,spans
from depth_server import DepthSource
from mcp_server import check
from ownership_review import compile_review,draft_hash,evidence_version
ROOT=base.ROOT
DRAFT_SCHEMA=json.loads((ROOT/'model/ownership.schema.json').read_text(encoding='utf-8'))
S={'type':'string'}
NOTE={'type':'object','additionalProperties':False,'required':['record_id','relevance','finding','span_ids'],'properties':{
    'record_id':S,'relevance':{'type':'string','enum':['material','contextual','irrelevant']},'finding':S,
    'span_ids':{'type':'array','items':S}}}
ATTRIBUTION={'type':'object','additionalProperties':False,'required':['actor','action','state','span_ids'],'properties':{'actor':S,'action':S,'state':{'type':'string','enum':['offered','requested','planned','in_progress','completed','reported','unknown']},'span_ids':{'type':'array','items':S,'minItems':1}}}
NOTE['required']+=['source_kind','attributions','attribution_limits']
NOTE['properties'].update(source_kind={'type':'string','enum':['evaluation','work','discussion','other']},attributions={'type':'array','items':ATTRIBUTION},attribution_limits=S)
TOOLS=copy.deepcopy(PRIOR_TOOLS)+[
    base.tool('writing_packet','Recover up to five already-read original records with exact spans and saved notes. Free local cache operation, available after source budget exhaustion. No new source access. Omit ids to return the next unnoted records.',{'ids':{'type':'array','items':S,'minItems':1,'maxItems':5}},[]),
    base.tool('save_notes','Persist up to five model judgments about already-read records. Exact span IDs required for material findings. Local journal only; never writes to an online source.',{'notes':{'type':'array','items':NOTE,'minItems':1,'maxItems':5}},['notes'])]
TOOLS[-1]['annotations']['readOnlyHint']=False
TOOLS.append(base.tool('draft_check','Check the complete draft against saved notes, source spans and derived coverage. Free local validation only; not a semantic grade. May be corrected within this same run. Does not seal the result.',{'draft':DRAFT_SCHEMA},['draft']))

def saved_notes(events):
    notes={}
    for event in events:
        if event['tool']=='save_notes' and not event['result'].get('error'):
            for note in event['arguments']['notes']:notes[note['record_id']]=note
    return notes

class OwnershipSource(DepthSource):
    def planning(self):
        p=super().planning();notes=saved_notes(self.events);full=self.full_reads()
        # Remove repeated inventories, not outstanding leads. Full originals remain recoverable.
        for key in ['full_read_index','subject_authored_full_records','attribution_review','priority_policy','stop_policy','later_use']:
            p.pop(key,None)
        p['writing']={'full_records':len(full),'noted_records':len(notes),'unnoted_ids':sorted(set(full)-set(notes)),
            'material_note_ids':sorted(id for id,n in notes.items() if n['relevance']=='material'),
            'recovery':'writing_packet and save_notes are free local operations within the 80-request ceiling, including after 45 source calls.'}
        p['writing']['checked_draft_current']=any(e['tool']=='draft_check' and e['result'].get('valid') and e['result'].get('evidence_version')==evidence_version(list(full.values()),self.events) for e in self.events)
        return p

    def finish(self):
        result=super().finish();missing=self.planning()['writing']['unnoted_ids']
        result['unresolved']['unnoted_records']=missing
        if missing and len(self.events)+1<REQUEST_LIMIT:
            result.update(allowed=False,status='continue_writing',receipt_id=None)
        elif not self.planning()['writing']['checked_draft_current'] and len(self.events)+1<REQUEST_LIMIT:
            result.update(allowed=False,status='check_draft',receipt_id=None)
        elif result['allowed']:
            result['receipt_id']=base.digest([result,[(e['sequence'],e['tool'],e['arguments']) for e in self.events]])
        return result

    def local(self,name,args):
        full=self.full_reads();notes=saved_notes(self.events)
        if name=='draft_check':
            review,p=compile_review(args['draft'],list(full.values()),self.events,draft=True)
            return {'valid':p['valid'],'errors':p['errors'],'draft_hash':draft_hash(args['draft']),'evidence_version':evidence_version(list(full.values()),self.events),'semantic_checked':False,'source_credit_records':p['source_credit_records']}
        if name=='writing_packet':
            ids=args.get('ids',sorted(set(full)-set(notes))[:5])
            if any(id not in full for id in ids):raise ValueError('Only full reads can be recovered')
            return {'records':[{'record':full[id],'citation_spans':spans(full[id]),'note':notes.get(id)} for id in ids],
                    'remaining_unnoted':len(set(full)-set(notes)-set(ids)),'cache_only':True}
        batch=args['notes'];seen=set()
        for note in batch:
            id=note['record_id']
            if id not in full or id in seen or not note['finding'].strip():raise ValueError('Invalid record note')
            seen.add(id);catalog={s['span_id'] for s in spans(full[id])}
            if any(s not in catalog for s in note['span_ids']):raise ValueError('Span outside original record')
            if note['relevance']=='material' and not note['span_ids']:raise ValueError('Material finding requires evidence')
            if note['relevance']=='material' and not note['attributions'] and not note['attribution_limits'].strip():raise ValueError('Explain absent attribution')
            for a in note['attributions']:
                if not a['actor'].strip() or not a['action'].strip() or not a['span_ids'] or any(s not in catalog for s in a['span_ids']):raise ValueError('Invalid attribution evidence')
        return {'saved_record_ids':sorted(seen),'cache_only':True}

    def execute(self,name,args):
        definition=next((t for t in TOOLS if t['name']==name),None)
        if not definition:raise ValueError('Tool outside allowlist')
        check(args,definition['inputSchema'])
        if len(self.events)>=REQUEST_LIMIT:return {'error':'request_limit_exhausted','planning':self.planning()}
        local=name in {'writing_packet','save_notes','research_status','finish_check','draft_check'}
        result=None if local else self.cached(name,args);hit=result is not None;charge=0 if local or hit else 1
        try:
            if name=='finish_check':result=self.finish()
            elif name=='research_status':result={'counts':{'source_calls':self.source_calls(),'requests_before_this_check':len(self.events)},'notes':saved_notes(self.events)}
            elif name in {'writing_packet','save_notes','draft_check'}:result=self.local(name,args)
            elif charge and self.source_calls()>=base.BUDGET:result={'error':'budget_exhausted','instruction':'Recover and reconcile cached evidence before finish_check.'};charge=0
            elif not hit:result=self.dispatch(name,args)
        except (ValueError,KeyError,TypeError):result={'error':'invalid_or_unavailable','detail':'Check source, observed IDs, exact spans or scope.'}
        self.decorate(result);result.update(cache_hit=hit,source_charge=charge,remaining_calls=base.BUDGET-self.source_calls()-charge)
        event={'sequence':len(self.events)+1,'tool':name,'arguments':args,'result':result,'source_charge':charge,'observed_at':datetime.now(timezone.utc).isoformat()}
        self.events.append(event);result['planning']=self.planning()
        with self.path.open('a',encoding='utf-8') as stream:stream.write(json.dumps(event,ensure_ascii=False)+'\n')
        return result

if __name__=='__main__':
    folder=ROOT/'runs/ownership';folder.mkdir(parents=True,exist_ok=True)
    log=(folder/'calls.jsonl').resolve();cp=(ROOT/'fixtures/ownership.corpus.json').resolve();sp=(ROOT/'fixtures/ownership.scope.json').resolve()
    schemas={ (ROOT/('model/'+name+'.schema.json')).resolve() for name in ['ownership','retention','depth','completion','attribution','review'] }
    base.guard({cp,sp}|schemas,log)
    server=OwnershipSource(json.loads(cp.read_text(encoding='utf-8')),json.loads(sp.read_text(encoding='utf-8')),log);base.TOOLS=TOOLS
    for line in sys.stdin:
        try:reply=base.respond(json.loads(line),server)
        except (ValueError,TypeError):reply={'jsonrpc':'2.0','id':None,'error':{'code':-32700,'message':'Parse error'}}
        if reply is not None:print(json.dumps(reply),flush=True)
