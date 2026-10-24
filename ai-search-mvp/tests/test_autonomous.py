import json,sys,tempfile,unittest,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from autonomous_server import ResearchSource,BUDGET,respond

def record(id,body='Original passage',parent=None,date='2040-01-10',source='chat'):
    return {'id':id,'source':source,'date':date,'author':'Contributor 01','container':'test-room','body':body,'parent':parent,'links':[],'title':'A test record','attachments':[],'link_only':False,'repost_of':None}

class AutonomousTests(unittest.TestCase):
    def setUp(self):
        self.scratch=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.scope={'start':'2040-01-01','end':'2040-01-31','horizon':'2040-02-28'}
        self.records=[record('chat:root',date='2039-11-01')]+[record('chat:reply'+str(i),'Reply '+str(i),parent='chat:root') for i in range(5)]+[record('docs:page','An unrelated page',source='docs'),record('chat:later','Later evidence',parent='chat:root',date='2040-03-01')]
        self.corpus={'synthetic':True,'sources':[{'id':'chat'},{'id':'docs'},{'id':'repo'}],'records':self.records,'attachments':[{'id':'docs:file','source':'docs','unavailable':True}]}
        self.path=Path(self.scratch.name)/'calls.jsonl'
        self.server=ResearchSource(self.corpus,self.scope,self.path)
    def tearDown(self):self.scratch.cleanup()
    def test_older_roots_discovered_by_current_activity(self):
        page=self.server.execute('list_roots',{'source':'chat'})
        self.assertEqual([r['id'] for r in page['items']],['chat:root'])
        self.assertNotIn('body',page['items'][0])
        self.assertTrue(page['items'][0]['has_children'])
    def test_paginated_context_does_not_automatically_read_everything(self):
        p=self.server.execute('read_context',{'source':'chat','id':'chat:root'})
        self.assertEqual(len(p['items']),3);self.assertFalse(p['end_reached'])
        q=self.server.execute('read_context',{'source':'chat','id':'chat:root','cursor':p['next_cursor']})
        self.assertEqual(len(q['items']),2);self.assertTrue(q['end_reached'])
        self.assertEqual(len(self.server.status()['full_record_ids']),5)
        self.assertNotIn('chat:root',self.server.status()['full_record_ids'])
    def test_search_is_snippet_not_a_full_read(self):
        self.server.execute('search',{'source':'chat','query':'reply'})
        self.assertEqual(self.server.status()['full_record_ids'],[])
        self.assertEqual(len(self.server.status()['snippet_only_ids']),3)
    def test_cursor_cannot_cross_queries(self):
        p=self.server.execute('search',{'source':'chat','query':'reply'})
        q=self.server.execute('search',{'source':'chat','query':'other','cursor':p['next_cursor']})
        self.assertEqual(q['error'],'invalid_or_unavailable')
    def test_horizon_and_private_path_read_are_rejected(self):
        for id in ['chat:later','../../private.json']:
            self.assertEqual(self.server.execute('read_record',{'source':'chat','id':id})['error'],'invalid_or_unavailable')
        with self.assertRaises(ValueError):self.server.execute('read_record',{'source':'chat','id':'chat:root','path':'anything'})
    def test_budget_persists_across_server_restart(self):
        for _ in range(BUDGET):self.server.execute('source_inventory',{})
        again=ResearchSource(self.corpus,self.scope,self.path)
        self.assertEqual(again.execute('read_record',{'source':'chat','id':'chat:root'})['error'],'budget_exhausted')
        self.assertEqual(len(again.events),BUDGET)
    def test_unavailable_attachment_not_empty_success(self):
        self.assertTrue(self.server.execute('read_attachment',{'source':'docs','id':'docs:file'})['unavailable'])
    def test_unknown_mutation_and_schema_rejected(self):
        for name in ['write_record','research_run','exec','read_file']:
            with self.assertRaises(ValueError):self.server.execute(name,{})
        response=respond({'jsonrpc':'2.0','id':1,'method':'tools/call','params':{'name':'read_file','arguments':{}}},self.server)
        self.assertTrue(response['result']['isError'])
    def test_server_guard_blocks_answer_key_and_network(self):
        script="from pathlib import Path;from autonomous_server import guard,ROOT;import socket;guard(set(),(ROOT/'runs/guard-test.jsonl').resolve());\nfor action in [lambda: (ROOT/'fixtures/autonomous.gold.json').read_text(),lambda: (ROOT.parent/'PRIVATE-NOT-OPENED').read_text(),lambda:socket.socket().connect(('127.0.0.1',9))]:\n try:action();raise AssertionError('boundary missed')\n except PermissionError:pass\nprint('blocked')"
        p=subprocess.run([sys.executable,'-c',script],cwd=ROOT,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr);self.assertIn('blocked',p.stdout)

if __name__=='__main__':unittest.main()
