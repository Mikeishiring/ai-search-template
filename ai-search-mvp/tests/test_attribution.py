import json,sys,tempfile,unittest,copy
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from attribution_server import AttributionSource,REQUEST_LIMIT
from attribution_review import validate
from test_autonomous import record

class AttributionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.path=Path(self.tmp.name)/'calls.jsonl'
        self.scope={'start':'2040-04-01','end':'2040-04-30','horizon':'2040-06-30','sources':['chat','docs','repo']}
        self.records=[record('chat:r',date='2040-04-02'),record('chat:c',parent='chat:r',date='2040-05-02'),record('chat:old',body='Earlier issue',date='2040-02-01'),record('chat:ancient',body='Earlier issue',date='2039-01-01'),record('chat:future',date='2041-01-01')]
        self.corpus={'synthetic':True,'sources':[{'id':s} for s in self.scope['sources']],'records':self.records,'attachments':[]}
        self.server=AttributionSource(self.corpus,self.scope,self.path)
    def tearDown(self):self.tmp.cleanup()
    def test_context_includes_unread_root_and_cache_avoids_source_read(self):
        p=self.server.execute('read_context',{'source':'chat','id':'chat:r'})
        self.assertEqual([r['id'] for r in p['items']],['chat:r','chat:c'])
        self.server.records={} # A cache hit must not consult the source again.
        q=self.server.execute('read_record',{'source':'chat','id':'chat:c'})
        self.assertTrue(q['cache_hit']);self.assertEqual(q['source_charge'],0)
        self.assertEqual(self.server.source_calls(),1);self.assertEqual(len(self.server.events),2)
    def test_exact_pages_replay_with_fresh_ledger_and_survive_restart(self):
        p=self.server.execute('list_roots',{'source':'chat','window':'earlier'})
        again=AttributionSource(self.corpus,self.scope,self.path)
        q=again.execute('list_roots',{'source':'chat','window':'earlier'})
        self.assertTrue(q['cache_hit']);self.assertEqual(p['items'],q['items'])
        self.assertEqual(q['planning']['requests_remaining'],REQUEST_LIMIT-2)
    def test_earlier_enumeration_is_bounded_but_search_reaches_farther(self):
        p=self.server.execute('list_roots',{'source':'chat','window':'earlier'})
        self.assertEqual([r['id'] for r in p['items']],['chat:old'])
        q=self.server.execute('search',{'source':'chat','window':'earlier','query':'Earlier'})
        self.assertEqual([r['id'] for r in q['items']],['chat:ancient','chat:old'])
    def test_wrong_source_and_unseen_file_do_not_hit_cache(self):
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        for source,id in [('docs','chat:r'),('chat','../../private'),('chat','chat:future')]:
            p=self.server.execute('read_record',{'source':source,'id':id})
            self.assertFalse(p['cache_hit']);self.assertIn('error',p)
    def test_request_ceiling_stops_free_cache_loop(self):
        for _ in range(REQUEST_LIMIT):self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.assertEqual(self.server.source_calls(),1)
        self.assertEqual(self.server.execute('read_record',{'source':'chat','id':'chat:r'})['error'],'request_limit_exhausted')
    def test_budget_exhaustion_cannot_be_bypassed_by_new_queries(self):
        for _ in range(45):self.server.execute('source_inventory',{})
        q=self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.assertEqual(q['error'],'budget_exhausted');self.assertEqual(self.server.source_calls(),45)
    def test_disposition_and_chain_validation_does_not_claim_semantic_truth(self):
        r=self.records[0]
        review={'account':'A summary','claims':[{'id':'c1','category':'contribution','statement':'A claim','limits':'Limited','evidence':[{'record_id':r['id'],'quote':r['body']}]}],'unknowns':[],'rejected_conclusions':[], 'attribution_chains':[{'intervention':'A change','roles':[{'actor':'Contributor 01','role':'Implemented','record_ids':[r['id']]}],'claim_ids':['c1'],'limits':'Limited'}], 'evidence_dispositions':[{'record_ids':[r['id']],'disposition':'used','claim_ids':['c1'],'reason':'Supports implementation'}]}
        result=validate(review,[r]);self.assertTrue(result['valid']);self.assertFalse(result['meaning_validated'])
        bad=copy.deepcopy(review);bad['evidence_dispositions']=[];self.assertFalse(validate(bad,[r])['valid'])
        bad=copy.deepcopy(review);bad['attribution_chains'][0]['roles'][0]['record_ids']=['chat:unknown'];self.assertFalse(validate(bad,[r])['valid'])

if __name__=='__main__':unittest.main()
