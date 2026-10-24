import json,sys,tempfile,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from completion_server import CompletionSource,spans,REQUEST_LIMIT
from completion_review import compile_review
from test_autonomous import record

class CompletionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.path=Path(self.tmp.name)/'calls.jsonl'
        self.scope={'start':'2040-04-01','end':'2040-04-30','horizon':'2040-06-30','sources':['chat']}
        self.records=[record('chat:r','Keep the trial running; revisit later. Next sentence.',date='2040-04-02'),record('chat:notice','A dependency failed, not the tool.',date='2040-04-03')]
        self.corpus={'synthetic':True,'sources':[{'id':'chat'}],'records':self.records,'attachments':[]};self.server=CompletionSource(self.corpus,self.scope,self.path)
    def tearDown(self):self.tmp.cleanup()
    def sweep(self):
        for w in ['earlier','primary','followup']:self.server.execute('list_roots',{'source':'chat','window':w})
    def test_clean_thread_queue_does_not_hide_unread_standalone(self):
        self.sweep();self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        result=self.server.execute('finish_check',{})
        self.assertFalse(result['allowed']);self.assertEqual(result['status'],'continue_research')
        self.assertEqual([r['id'] for r in result['unresolved']['unread_surfaced_records']],['chat:notice'])
        self.assertGreater(result['counts']['source_calls_remaining'],0)
    def test_free_audits_and_cached_reads_keep_authoritative_budget(self):
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.server.execute('research_status',{})
        result=self.server.execute('finish_check',{})
        self.assertEqual(result['counts']['source_calls'],1)
        self.assertEqual(result['counts']['requests_including_this_check'],4)
    def test_exhaustion_reports_incomplete_not_complete(self):
        self.sweep()
        while self.server.source_calls()<45:self.server.execute('source_inventory',{})
        result=self.server.execute('finish_check',{})
        self.assertTrue(result['allowed']);self.assertEqual(result['status'],'source_limit')
        self.assertEqual(len(result['unresolved']['unread_surfaced_records']),2)
    def test_full_observed_discovery_allows_early_stop_with_spare_calls(self):
        self.sweep()
        for r in self.records:self.server.execute('read_record',{'source':'chat','id':r['id']})
        result=self.server.execute('finish_check',{})
        self.assertTrue(result['allowed']);self.assertEqual(result['status'],'observed_scope_complete')
        self.assertEqual(result['counts']['source_calls_remaining'],40)
    def test_spans_preserve_punctuation_unicode_and_revision(self):
        r=record('chat:test','Wait; do not change this. Same. Same. A → B.')
        ss=spans(r)
        self.assertEqual(ss[0]['quote'],'Wait; do not change this.')
        self.assertTrue(all(r['body'][s['start']:s['end']]==s['quote'] for s in ss))
        self.assertEqual(len({s['span_id'] for s in ss}),len(ss))
        changed=copy.deepcopy(r);changed['body']=changed['body'].replace(';','.')
        self.assertNotEqual(spans(changed)[0]['span_id'],ss[0]['span_id'])
    def test_no_unseen_records_in_completion_leads(self):
        self.assertEqual(self.server.planning()['unread_surfaced_records'],[])
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.assertNotIn('chat:notice',json.dumps(self.server.planning()))
    def test_compiler_rejects_invented_spans_and_stale_stop_receipt(self):
        self.sweep()
        for r in self.records:self.server.execute('read_record',{'source':'chat','id':r['id']})
        receipt=self.server.execute('finish_check',{})
        raw={'account':'A constrained trial','claims':[{'id':'c1','category':'mandate','statement':'Keep the trial running','limits':'Revisit later','evidence':[{'record_id':'chat:r','span_id':spans(self.records[0])[0]['span_id']}]}],'unknowns':[],'rejected_conclusions':[],'attribution_chains':[{'intervention':'Trial','roles':[{'actor':'Contributor 01','role':'Gave the instruction','record_ids':['chat:r']}],'claim_ids':['c1'],'limits':'Limited'}],'evidence_dispositions':[{'record_ids':['chat:r'],'disposition':'used','claim_ids':['c1'],'reason':'Mandate'},{'record_ids':['chat:notice'],'disposition':'contextual','claim_ids':[],'reason':'Dependency context'}],'attachment_dispositions':[],'stop_receipt_id':receipt['receipt_id']}
        review,valid=compile_review(raw,self.records,self.server.events)
        self.assertTrue(valid['valid']);self.assertEqual(review['claims'][0]['evidence'][0]['quote'],'Keep the trial running; revisit later.')
        broken=copy.deepcopy(raw);broken['claims'][0]['evidence'][0]['span_id']='invented'
        self.assertFalse(compile_review(broken,self.records,self.server.events)[1]['valid'])
        self.server.execute('research_status',{})
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['completion_receipt_valid'])

if __name__=='__main__':unittest.main()
