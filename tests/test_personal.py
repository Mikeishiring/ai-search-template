import copy,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import personal

class PersonalWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=personal.PROJECT.parent,prefix='.synthetic-test-')
        self.root=Path(self.temp.name);self.workspace=self.root/'private-evidence'
        personal.init(self.workspace,'My evidence',synthetic=True)
        self.record={'source':'chat','id':'1','title':'Proposal','date':'2030-01-01','author':'Contributor 01','text':'I can draft it. It has not shipped.'}
    def tearDown(self):self.temp.cleanup()
    def add(self):
        return personal.add_claim(self.workspace,'chat','1','Contributor 01 offered a draft.','Contributor 01','offered','I can draft it.','No delivery evidence.')
    def test_public_checkout_is_refused(self):
        with self.assertRaises(ValueError):personal.init(personal.PROJECT/'private-test','No')
    def test_existing_workspace_is_not_overwritten(self):
        before=(self.workspace/'workspace.json').read_bytes()
        with self.assertRaises(ValueError):personal.init(self.workspace,'Changed')
        self.assertEqual(before,(self.workspace/'workspace.json').read_bytes())
    def test_roundtrip_dedup_and_safe_render(self):
        raw=copy.deepcopy(self.record);raw['title']='<script>alert(1)</script>'
        self.assertEqual(personal.import_records(self.workspace,[raw])['new_versions'],1)
        self.assertEqual(personal.import_records(self.workspace,[raw])['unchanged'],1)
        self.add();self.add()
        result=personal.build(self.workspace);self.assertEqual(result['claims'],1)
        output=(self.workspace/'DASHBOARD.html').read_text(encoding='utf-8')
        self.assertIn('&lt;script&gt;',output);self.assertNotIn('<script>',output)
        self.assertEqual(output.count('Synthetic demo data'),1)
        self.assertIn("default-src 'none'",output);self.assertIn('still need human review',output)
    def test_changed_source_keeps_old_quote_and_flags_staleness(self):
        personal.import_records(self.workspace,[self.record]);self.add()
        newer=self.record|{'text':'The draft is ready.'}
        personal.import_records(self.workspace,[newer])
        self.assertEqual(personal.build(self.workspace)['stale_claims'],1)
        personal.import_records(self.workspace,[self.record])
        self.assertEqual(personal.build(self.workspace)['stale_claims'],1)
        self.assertIn('I can draft it.',(self.workspace/'DASHBOARD.html').read_text())
    def test_invalid_batch_is_atomic(self):
        before=(self.workspace/'records.json').read_bytes()
        for invalid_date in ['not-a-date','20300101','2030-W01-1']:
            with self.assertRaises(ValueError):personal.import_records(self.workspace,[self.record,self.record|{'id':'2','date':invalid_date}])
            self.assertEqual(before,(self.workspace/'records.json').read_bytes())
    def test_raw_exports_and_duplicate_source_keys_refused(self):
        with self.assertRaises(ValueError):personal.import_records(self.workspace,{'messages':[self.record]})
        with self.assertRaises(ValueError):personal.import_records(self.workspace,[self.record,self.record])
    def test_forged_quote_refused(self):
        personal.import_records(self.workspace,[self.record])
        with self.assertRaises(ValueError):personal.add_claim(self.workspace,'chat','1','Delivered.','Contributor 01','completed','It shipped.','None.')
    def test_ambiguous_quote_needs_offset(self):
        personal.import_records(self.workspace,[self.record|{'text':'Same. Same.'}])
        with self.assertRaises(ValueError):personal.add_claim(self.workspace,'chat','1','Reported.','Contributor 01','reported','Same.','Limited.')
        personal.add_claim(self.workspace,'chat','1','Reported.','Contributor 01','reported','Same.','Limited.',6)
        self.assertEqual(personal.build(self.workspace)['claims'],1)
    def test_mutated_source_and_unsafe_url_refused(self):
        with self.assertRaises(ValueError):personal.import_records(self.workspace,[self.record|{'url':'javascript:alert(1)'}])
        personal.import_records(self.workspace,[self.record]);self.add()
        store=json.loads((self.workspace/'records.json').read_text());next(iter(store['versions'].values()))['text']='Changed'
        (self.workspace/'records.json').write_text(json.dumps(store))
        with self.assertRaises(ValueError):personal.build(self.workspace)
    def test_no_network_or_subprocess_dependency(self):
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')),patch('subprocess.Popen',side_effect=AssertionError('Process forbidden')):
            personal.import_records(self.workspace,[self.record]);self.add();personal.build(self.workspace)

if __name__=='__main__':unittest.main()
