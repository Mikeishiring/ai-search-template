import copy,sys,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from ownership_server import OwnershipSource
from ownership_review import compile_review
from completion_server import spans
from test_autonomous import record

class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.records=[record('chat:r','I can add the export.',date='2040-04-02'),record('docs:e','Six samples passed. No general effect is established.',source='docs',date='2040-04-03')]
        self.records[1]['author']='Contributor 02'
        self.scope={'start':'2040-04-01','end':'2040-04-30','horizon':'2040-06-30','sources':['chat','docs'],'subject':'Contributor 01'}
        self.server=OwnershipSource({'synthetic':True,'sources':[{'id':'chat'},{'id':'docs'}],'records':self.records,'attachments':[]},self.scope,Path(self.tmp.name)/'calls.jsonl')
    def tearDown(self):self.tmp.cleanup()
    def setup_draft(self):
        for source in self.scope['sources']:
            for window in ['earlier','primary','followup']:self.server.execute('list_roots',{'source':source,'window':window})
        for r in self.records:self.server.execute('read_record',{'source':r['source'],'id':r['id']})
        notes=[]
        for r in self.records:
            ids=[s['span_id'] for s in spans(r)]
            notes.append({'record_id':r['id'],'relevance':'material','finding':r['body'],'span_ids':ids,'source_kind':'evaluation' if r['source']=='docs' else 'work','attributions':[{'actor':r['author'],'action':'supply an export' if r['source']=='chat' else 'report the sample result','state':'offered' if r['source']=='chat' else 'reported','span_ids':ids}],'attribution_limits':'Author does not imply sole performance.'})
        self.assertNotIn('error',self.server.execute('save_notes',{'notes':notes}))
        claims=[{'id':'c'+str(i),'category':'contribution' if i==0 else 'outcome','statement':'An export was offered.' if i==0 else 'Six samples passed.','limits':'Delivery is unconfirmed.' if i==0 else 'No general effect is established.','evidence':[{'record_id':r['id'],'span_id':s['span_id']} for s in spans(r)],'roles':[{'record_id':r['id'],'attribution_index':0}]} for i,r in enumerate(self.records)]
        return {'claims':claims,'unknowns':[],'rejected_conclusions':[],'stop_receipt_id':'pending','research_choices':[],'story_order':['c0','c1'],'coverage_notes':[]}
    def seal(self,raw):
        checked=self.server.execute('draft_check',{'draft':raw});self.assertTrue(checked['valid'],checked)
        receipt=self.server.execute('finish_check',{});self.assertTrue(receipt['allowed'],receipt)
        raw=copy.deepcopy(raw);raw['stop_receipt_id']=receipt['receipt_id'];return raw
    def test_report_author_is_credited_without_inventing_measurer(self):
        raw=self.seal(self.setup_draft());review,p=compile_review(raw,self.records,self.server.events)
        self.assertTrue(p['valid'],p['errors']);self.assertIn('Evaluation source was written by Contributor 02.',review['account'])
        self.assertEqual(review['source_credits']['c1'][0]['basis'],'source author metadata; not proof of sole measurement work')
    def test_saved_offer_state_survives_role_compilation(self):
        raw=self.seal(self.setup_draft());review,p=compile_review(raw,self.records,self.server.events)
        self.assertEqual(review['attribution_chains'][0]['roles'][0]['role'],'offered: supply an export')
    def test_cited_coverage_note_is_not_a_whole_record_omission(self):
        raw=self.setup_draft();raw['coverage_notes']=[{'record_id':'docs:e','reason':'Extra background is outside scope.'}]
        raw=self.seal(raw);review,p=compile_review(raw,self.records,self.server.events)
        self.assertTrue(p['valid']);self.assertEqual(review['omitted_material'],[]);self.assertEqual(len(review['partial_coverage_notes']),1)
    def test_absent_material_still_requires_explanation(self):
        raw=self.setup_draft();raw['claims'].pop();raw['story_order'].pop()
        self.assertFalse(self.server.execute('draft_check',{'draft':raw})['valid'])
        raw['coverage_notes']=[{'record_id':'docs:e','reason':'Deliberate exclusion to be reviewed.'}]
        raw=self.seal(raw);review,p=compile_review(raw,self.records,self.server.events)
        self.assertTrue(p['valid']);self.assertEqual(review['omitted_material'],raw['coverage_notes'])
    def test_cannot_finish_before_draft_check(self):
        self.setup_draft();receipt=self.server.execute('finish_check',{})
        self.assertFalse(receipt['allowed']);self.assertEqual(receipt['status'],'check_draft')
    def test_changing_final_wording_invalidates_checked_draft(self):
        raw=self.seal(self.setup_draft());raw['claims'][0]['statement']='The export was delivered.'
        self.assertFalse(compile_review(raw,self.records,self.server.events)[1]['valid'])
    def test_changed_notes_invalidate_draft(self):
        raw=self.setup_draft();self.assertTrue(self.server.execute('draft_check',{'draft':raw})['valid'])
        note=copy.deepcopy(next(e for e in self.server.events if e['tool']=='save_notes')['arguments']['notes'][0]);note['finding']='A revised interpretation.'
        self.server.execute('save_notes',{'notes':[note]})
        self.assertEqual(self.server.execute('finish_check',{})['status'],'check_draft')
    def test_role_must_cite_saved_attribution_spans(self):
        raw=self.setup_draft();raw['claims'][0]['evidence']=raw['claims'][1]['evidence']
        self.assertFalse(self.server.execute('draft_check',{'draft':raw})['valid'])

if __name__=='__main__':unittest.main()
