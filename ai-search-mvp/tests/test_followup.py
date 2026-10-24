import json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from followup_server import FollowupSource
from test_autonomous import record

class FollowupTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.path=Path(self.tmp.name)/'calls.jsonl'
        self.scope={'start':'2040-01-01','end':'2040-01-31','horizon':'2040-02-28','sources':['chat','docs','repo']}
        root=record('chat:r');root['links']=[{'source':'repo','id':'repo:linked'}];root['attachments']=['chat:file']
        self.corpus={'synthetic':True,'sources':[{'id':s} for s in self.scope['sources']], 'records':[root]+[record('chat:c'+str(i),parent='chat:r',date='2040-02-03') for i in range(4)]+[record('chat:nested',parent='chat:c0'),record('docs:new',source='docs',date='2040-02-05'),record('repo:linked',source='repo'),record('chat:secret',date='2041-01-01')], 'attachments':[{'id':'chat:file','source':'chat','unavailable':True}]}
        self.server=FollowupSource(self.corpus,self.scope,self.path)
    def tearDown(self):self.tmp.cleanup()
    def test_ledger_only_contains_observed_leads(self):
        self.assertEqual(self.server.planning()['unopened_contexts'],[])
        p=self.server.execute('read_record',{'source':'chat','id':'chat:r'})['planning']
        self.assertEqual([r['id'] for r in p['unopened_contexts']],['chat:r'])
        self.assertEqual(p['unread_references'],[{'source':'repo','id':'repo:linked'}])
        self.assertNotIn('docs:new',json.dumps(p));self.assertNotIn('chat:secret',json.dumps(p))
    def test_context_obligation_survives_pagination_and_nested_children(self):
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        p=self.server.execute('read_context',{'source':'chat','id':'chat:r'})
        self.assertIn('chat:r',[r['id'] for r in p['planning']['unopened_contexts']])
        q=self.server.execute('read_context',{'source':'chat','id':'chat:r','cursor':p['next_cursor']})
        self.assertEqual([r['id'] for r in q['planning']['unopened_contexts']],['chat:c0'])
        self.assertEqual(q['planning']['pending_pages'],[])
    def test_followup_sweep_finds_new_roots(self):
        p=self.server.execute('list_roots',{'source':'docs','window':'primary'})
        self.assertEqual(p['items'],[])
        q=self.server.execute('list_roots',{'source':'docs','window':'followup'})
        self.assertEqual([r['id'] for r in q['items']],['docs:new'])
        self.assertNotIn({'source':'docs','window':'followup'},q['planning']['unfinished_window_sweeps'])
    def test_reference_and_unavailable_attachment_are_closed_by_explicit_reads(self):
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.server.execute('read_record',{'source':'repo','id':'repo:linked'})
        q=self.server.execute('read_attachment',{'source':'chat','id':'chat:file'})
        self.assertTrue(q['unavailable']);self.assertEqual(q['planning']['unchecked_attachments'],[])
        self.assertEqual(q['planning']['unread_references'],[])
    def test_ledger_persists_and_cannot_read_arbitrary_files(self):
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        again=FollowupSource(self.corpus,self.scope,self.path)
        self.assertEqual(again.planning(),self.server.planning())
        self.assertEqual(again.execute('read_record',{'source':'chat','id':'../../private'})['error'],'invalid_or_unavailable')
        with self.assertRaises(ValueError):again.execute('write_record',{})
    def test_followup_includes_old_root_with_later_reply(self):
        q=self.server.execute('list_roots',{'source':'chat','window':'followup'})
        self.assertEqual([r['id'] for r in q['items']],['chat:r'])
        self.assertEqual(self.server.status()['full_record_ids'],[])

if __name__=='__main__':unittest.main()
