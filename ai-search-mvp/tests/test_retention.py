import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from retention_server import RetentionSource,saved_notes
from retention_review import compile_review
from completion_server import spans
from test_autonomous import record

class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs');self.path=Path(self.tmp.name)/'calls.jsonl'
        self.records=[record('chat:r','I diagnosed the fault. The later fix passed six checks.',date='2040-04-02'),record('chat:x','This does not prove wider use.',date='2040-04-03')]
        self.scope={'start':'2040-04-01','end':'2040-04-30','horizon':'2040-06-30','sources':['chat'],'subject':'Contributor 01'}
        self.corpus={'synthetic':True,'sources':[{'id':'chat'}],'records':self.records,'attachments':[]}
        self.server=RetentionSource(self.corpus,self.scope,self.path)
    def tearDown(self):self.tmp.cleanup()
    def read_all(self):
        for w in ['earlier','primary','followup']:self.server.execute('list_roots',{'source':'chat','window':w})
        for r in self.records:self.server.execute('read_record',{'source':'chat','id':r['id']})
    def note(self,r):return {'record_id':r['id'],'relevance':'material','finding':r['body'],'span_ids':[s['span_id'] for s in spans(r)]}
    def draft(self):
        self.read_all();self.server.execute('save_notes',{'notes':[self.note(r) for r in self.records]})
        receipt=self.server.execute('finish_check',{})
        return {'claims':[{'id':'c1','category':'contribution','statement':'Contributor 01 diagnosed the fault and the fix passed six checks.','limits':'This was one constrained trial.','evidence':[{'record_id':'chat:r','span_id':s['span_id']} for s in spans(self.records[0])],'roles':[{'actor':'Contributor 01','role':'Diagnosed the fault','evidence_indices':[0]}]}],'story_order':['c1'],'unknowns':[],'rejected_conclusions':[{'statement':'Wider use was proved.','reason':'The record explicitly limits that conclusion.','record_ids':['chat:x']}],'omitted_material':[],'stop_receipt_id':receipt['receipt_id'],'research_choices':[]}
    def test_cache_does_not_reveal_unread_records(self):
        result=self.server.execute('writing_packet',{'ids':['chat:r']});self.assertIn('error',result)
        self.assertEqual(self.server.execute('writing_packet',{})['records'],[])
    def test_recovery_works_after_source_limit(self):
        self.read_all()
        while self.server.source_calls()<45:self.server.execute('source_inventory',{})
        result=self.server.execute('finish_check',{});self.assertEqual(result['status'],'continue_writing');self.assertFalse(result['allowed'])
        packet=self.server.execute('writing_packet',{});self.assertEqual(len(packet['records']),2);self.assertEqual(self.server.source_calls(),45)
        self.server.execute('save_notes',{'notes':[self.note(r) for r in self.records]})
        self.assertTrue(self.server.execute('finish_check',{})['allowed'])
    def test_notes_survive_restart_and_have_exact_spans(self):
        self.read_all();self.server.execute('save_notes',{'notes':[self.note(self.records[0])]})
        restarted=RetentionSource(self.corpus,self.scope,self.path)
        self.assertEqual(saved_notes(restarted.events)['chat:r'],self.note(self.records[0]))
        self.assertEqual(restarted.execute('writing_packet',{'ids':['chat:r']})['records'][0]['citation_spans'],spans(self.records[0]))
    def test_invalid_note_batch_is_atomic(self):
        self.read_all();bad=self.note(self.records[1]);bad['span_ids']=['invented']
        self.assertIn('error',self.server.execute('save_notes',{'notes':[self.note(self.records[0]),bad]}))
        self.assertEqual(saved_notes(self.server.events),{})
    def test_rejection_only_record_is_accounted_for(self):
        raw=self.draft();review,p=compile_review(raw,self.records,self.server.events)
        self.assertTrue(p['valid'],p['errors']);self.assertEqual(p['rejection_only_records'],['chat:x'])
        self.assertEqual(p['material_notes_represented'],2)
        self.assertEqual(review['account'],raw['claims'][0]['statement']+' '+raw['claims'][0]['limits'])
    def test_story_cannot_drop_a_claim(self):
        raw=self.draft();raw['story_order']=[]
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
    def test_material_note_cannot_silently_disappear(self):
        raw=self.draft();raw['rejected_conclusions']=[]
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
        raw['omitted_material']=[{'record_id':'chat:x','reason':'A deliberate question-scope exclusion, inspectable by the evaluator.'}]
        self.assertTrue(compile_review(raw,self.records,self.server.events)[1]['valid'])
    def test_unknown_rejection_record_remains_invalid(self):
        raw=self.draft();raw['rejected_conclusions'][0]['record_ids']=['chat:invented']
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])

if __name__=='__main__':unittest.main()
