import copy,json,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from depth_server import DepthSource
from depth_review import compile_review
from completion_server import spans
from test_autonomous import record

class DepthTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.records=[record('chat:r','I investigated the mismatch.',date='2040-04-02'),record('chat:c','The repair was accepted.',parent='chat:r',date='2040-04-03'),record('chat:d','Keep the manual check.',parent='chat:c',date='2040-04-04'),record('chat:x','Lunch moved.',date='2040-04-05')]
        self.scope={'start':'2040-04-01','end':'2040-04-30','horizon':'2040-06-30','sources':['chat'],'subject':self.records[0]['author']}
        self.server=DepthSource({'synthetic':True,'sources':[{'id':'chat'}],'records':self.records,'attachments':[]},self.scope,Path(self.tmp.name)/'calls.jsonl')
    def tearDown(self):self.tmp.cleanup()
    def ready(self):
        for w in ['earlier','primary','followup']:self.server.execute('list_roots',{'source':'chat','window':w})
        for id in ['chat:r','chat:c']:self.server.execute('read_context',{'source':'chat','id':id})
        self.server.execute('read_record',{'source':'chat','id':'chat:x'})
        receipt=self.server.execute('finish_check',{})
        return {'account':'Investigation and limited repair.','claims':[{'id':'C1','category':'contribution','statement':'Contributor 01 investigated the mismatch.','limits':'No claim of sole implementation.','evidence':[{'record_id':'chat:r','span_id':spans(self.records[0])[0]['span_id']}],'roles':[{'actor':'Contributor 01','role':'Investigated','evidence_indices':[0]}]}],'unknowns':[],'rejected_conclusions':[],'stop_receipt_id':receipt['receipt_id'],'uncited_records':[{'record_id':r['id'],'disposition':'contextual','reason':'Read supporting context without quoting it.'} for r in self.records[1:]],'research_choices':[]}
    def test_priority_uses_only_observed_depth(self):
        self.assertEqual(self.server.planning()['priority_branches'],[])
        self.server.execute('read_context',{'source':'chat','id':'chat:r'})
        p=self.server.planning();self.assertEqual(p['priority_branches'][0]['arguments']['id'],'chat:c');self.assertEqual(p['priority_branches'][0]['observed_depth'],1)
        self.assertNotIn('chat:d',json.dumps(p));self.assertNotIn('chat:x',json.dumps(p))
    def test_subject_index_only_full_reads(self):
        self.server.execute('list_roots',{'source':'chat','window':'primary'})
        self.assertEqual(self.server.planning()['subject_authored_full_records'],[])
        self.server.execute('read_record',{'source':'chat','id':'chat:r'})
        self.assertEqual([r['id'] for r in self.server.planning()['subject_authored_full_records']],['chat:r'])
    def test_compiler_derives_links_and_one_disposition_per_record(self):
        raw=self.ready();review,p=compile_review(raw,self.records,self.server.events)
        self.assertTrue(p['valid'],p['errors']);self.assertEqual(len(review['evidence_dispositions']),4)
        self.assertEqual(review['attribution_chains'][0]['roles'][0]['record_ids'],['chat:r'])
        self.assertEqual(review['attribution_chains'][0]['claim_ids'],['C1'])
        self.assertEqual(review['attachment_dispositions'],[])
    def test_missing_omission_remains_failure(self):
        raw=self.ready();raw['uncited_records'].pop()
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
    def test_invalid_role_index_not_silently_repaired(self):
        raw=self.ready();raw['claims'][0]['roles'][0]['evidence_indices']=[99]
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
    def test_duplicate_or_cited_omission_rejected(self):
        raw=self.ready();raw['uncited_records'].append(copy.deepcopy(raw['uncited_records'][0]))
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
        raw=self.ready();raw['uncited_records'].append({'record_id':'chat:r','disposition':'unresolved','reason':'Its child is missing'})
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])

if __name__=='__main__':unittest.main()
