"""Fail-closed source selection, local persistence and model-processing choice."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import local_context as local
from research_sheet import write_json, read_json
from research_sheet_server import LocalSheetSource


class LocalContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.export = self.folder / 'selected.json'
        self.workspace = self.folder / 'context'
        self.policy = {'subject': 'Contributor 01', 'question': 'Understand the desk trial',
            'earlier_start': '2032-01-01', 'start': '2032-02-01', 'end': '2032-03-31', 'horizon': '2032-05-31',
            'locations': [{'source': 'chat', 'container': 'desk-channel', 'kind': 'channel'}],
            'import_files': [str(self.export)], 'allow_dms': False, 'allow_private_channels': False,
            'allow_attachments': False, 'retain_source_text': True, 'model_processing': 'local_only'}
        self.record = {'id': 'chat:one', 'source': 'chat', 'container': 'desk-channel', 'kind': 'channel',
            'date': '2032-02-03', 'author': 'Contributor 01', 'title': 'Desk decision', 'body': 'I built the form.',
            'parent': None, 'links': [], 'attachments': []}

    def start(self, records=None, policy=None):
        write_json(self.export, {'records': records if records is not None else [self.record], 'attachments': []})
        local.initialize(self.workspace, policy or self.policy)
        return local.import_export(self.workspace, self.export)

    def test_setup_and_capture_are_local_and_model_access_defaults_off(self):
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            self.start()
            result = local.status(self.workspace)
        self.assertEqual(result['locations'][0]['captured'], 1)
        self.assertEqual(result['locations'][0]['read_in_research'], 0)
        self.assertTrue((self.workspace / 'CAREER-CONTEXT.html').is_file())
        self.assertTrue(all(v == 'needs_review' for v in result['checklist'].values()))
        with self.assertRaises(ValueError): local.load(self.workspace, for_model=True)

    def test_denied_locations_dms_private_channels_and_dates_never_persist(self):
        records = [self.record]
        for i, change in enumerate([{'container': 'dm-01', 'kind': 'dm'},
                                   {'container': 'secret', 'kind': 'private_channel'},
                                   {'date': '2032-06-01'}, {'date': '2031-12-31'}, {'container': 'other'}]):
            records.append(self.record | change | {'id': 'chat:excluded-' + str(i), 'body': 'EXCLUDED_BODY_' + str(i)})
        result = self.start(records)
        self.assertEqual(result['skipped_records'], 5)
        self.assertEqual(result['retained_records'], 1)
        for path in self.workspace.iterdir():
            if path.is_file(): self.assertNotIn('EXCLUDED_BODY_', path.read_text(encoding='utf-8'))

    def test_dm_switch_does_not_enable_unselected_conversations(self):
        policy = copy.deepcopy(self.policy)
        policy['allow_dms'] = True
        policy['locations'].append({'source': 'chat', 'container': 'dm-01', 'kind': 'dm'})
        records = [self.record | {'id': 'chat:dm-1', 'kind': 'dm', 'container': 'dm-01'},
                   self.record | {'id': 'chat:dm-2', 'kind': 'dm', 'container': 'dm-02'}]
        self.assertEqual(self.start(records, policy)['retained_records'], 1)
        policy['allow_dms'] = False
        with self.assertRaises(ValueError): local.validate_policy(policy)

    def test_unknown_privacy_kind_and_unselected_file_fail_before_capture(self):
        local.initialize(self.workspace, self.policy)
        with patch.object(local.personal, 'read_json', wraps=local.personal.read_json) as read:
            with self.assertRaises(ValueError): local.import_export(self.workspace, self.folder / 'unselected.json')
            self.assertNotIn(self.folder / 'unselected.json', [call.args[0] for call in read.call_args_list])
        write_json(self.export, {'records': [self.record | {'kind': 'unknown'}]})
        with self.assertRaises(ValueError): local.import_export(self.workspace, self.export)
        self.assertEqual(read_json(self.workspace / 'corpus.json')['records'], [])

    def test_metadata_only_never_retains_bodies_or_serves_model(self):
        policy = self.policy | {'retain_source_text': False, 'model_processing': 'selected_sources'}
        self.start([self.record | {'body': 'BODY_MUST_NOT_BE_SAVED'}], policy)
        self.assertNotIn('BODY_MUST_NOT_BE_SAVED', (self.workspace / 'corpus.json').read_text())
        with self.assertRaises(ValueError): local.load(self.workspace, for_model=True)

    def test_model_allowed_source_only_reads_selected_capture_and_returns_non_synthetic(self):
        self.start(policy=self.policy | {'model_processing': 'selected_sources'})
        workspace, _, corpus, scope, policy = local.load(self.workspace, for_model=True)
        source = LocalSheetSource(corpus, scope, workspace / 'calls.jsonl', policy)
        self.assertFalse(source.execute('source_inventory', {})['synthetic'])
        self.assertEqual(source.execute('read_record', {'source': 'chat', 'id': 'chat:one'})['items'][0]['body'], self.record['body'])
        self.assertIn('error', source.execute('read_record', {'source': 'chat', 'id': 'chat:not-selected'}))
        with self.assertRaises(ValueError): local.import_export(self.workspace, self.export)

    def test_policy_tampering_blocks_serving(self):
        self.start()
        policy = read_json(self.workspace / 'policy.json')
        policy['model_processing'] = 'selected_sources'
        write_json(self.workspace / 'policy.json', policy)
        with self.assertRaises(ValueError): local.load(self.workspace, for_model=True)

    def test_revocation_stops_an_already_running_server_and_cached_reads(self):
        self.start(policy=self.policy | {'model_processing': 'selected_sources'})
        workspace, _, corpus, scope, policy = local.load(self.workspace, for_model=True)
        source = LocalSheetSource(corpus, scope, workspace / 'calls.jsonl', policy)
        source.execute('read_record', {'source': 'chat', 'id': 'chat:one'})
        policy['model_processing'] = 'local_only'
        write_json(workspace / 'policy.json', policy)
        self.assertEqual(source.execute('writing_packet', {'ids': ['chat:one']})['error'], 'policy_changed')
        self.assertEqual(source.execute('read_record', {'source': 'chat', 'id': 'chat:one'})['error'], 'policy_changed')
        self.assertEqual(source.execute('research_probe', {'account_id': 'desk', 'lens': 'origins',
            'question': 'What preceded the form?', 'source': 'chat', 'query': 'form'})['error'], 'policy_changed')

    def test_attachment_content_excluded_and_missing_parent_is_not_followed(self):
        record = self.record | {'attachments': ['chat:file'], 'parent': 'chat:excluded-parent'}
        write_json(self.export, {'records': [record], 'attachments': [{'id': 'chat:file', 'source': 'chat',
            'title': 'File', 'body': 'ATTACHMENT_BODY', 'unavailable': False}]})
        local.initialize(self.workspace, self.policy)
        local.import_export(self.workspace, self.export)
        corpus = read_json(self.workspace / 'corpus.json')
        self.assertEqual(corpus['records'][0]['parent'], None)
        self.assertEqual(corpus['attachments'], [])
        self.assertNotIn('ATTACHMENT_BODY', json.dumps(corpus))

    def test_stdio_server_enforces_model_opt_in(self):
        self.start()
        response = subprocess.run([sys.executable, str(ROOT / 'research_sheet_server.py'), str(self.workspace)],
            input=b'{"jsonrpc":"2.0","id":1,"method":"tools/list"}\n', capture_output=True, timeout=15)
        self.assertNotEqual(response.returncode, 0)
        self.assertNotIn(b'"tools":', response.stdout)

    def test_missing_parent_chain_is_order_independent_and_repeatable(self):
        child = self.record | {'id': 'chat:child', 'parent': 'chat:one'}
        parent = self.record | {'parent': 'chat:excluded-parent'}
        self.start([child, parent])
        first = read_json(self.workspace / 'corpus.json')
        self.assertEqual(first['records'][0]['parent'], 'chat:one')
        self.assertIsNone(first['records'][1]['parent'])
        self.assertEqual(first['records'][1]['links'], [{'source': 'chat', 'id': 'chat:excluded-parent'}])
        local.import_export(self.workspace, self.export)
        self.assertEqual(first, read_json(self.workspace / 'corpus.json'))

    def test_stdio_utf8_preserves_non_ascii_notes(self):
        self.start(policy=self.policy | {'model_processing': 'selected_sources'})
        import narrative_retention as retention
        from completion_server import spans
        record = read_json(self.workspace / 'corpus.json')['records'][0]
        section = retention.sections(record, spans)[0]
        text = 'Meaning \u2013 caf\u00e9 form construction was reported.'
        note = {'section_id': section['section_id'], 'finding': text,
                'span_ids': [s['span_id'] for s in section['citation_spans']],
                'disposition': 'context', 'events': [],
                'reason': 'This transport fixture is testing Unicode preservation only.'}
        requests = [{'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {'name': 'read_record', 'arguments': {'source': 'chat', 'id': 'chat:one'}}},
                    {'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {'name': 'save_extraction', 'arguments': {'sections': [note]}}}]
        result = subprocess.run([sys.executable, str(ROOT / 'research_sheet_server.py'), str(self.workspace)],
            input=('\n'.join(json.dumps(r, ensure_ascii=False) for r in requests) + '\n').encode('utf-8'), capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
        journal = [json.loads(l) for l in (self.workspace / 'calls.jsonl').read_text('utf-8').splitlines()]
        self.assertTrue(journal[-1]['result']['valid'])
        self.assertEqual(journal[-1]['result']['notes'][0]['finding'], text)


if __name__ == '__main__': unittest.main()
