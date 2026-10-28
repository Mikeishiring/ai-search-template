"""Bounded extraction, source privacy, failure preservation and journal integration."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import extraction_batches as batches
import local_context
from research_sheet import read_json, write_json
from research_sheet_server import LocalSheetSource


class ExtractionBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.workspace = self.folder / 'context'
        self.export = self.folder / 'selected.json'
        self.policy = {'subject': 'Contributor 01', 'question': 'Understand the desk trial',
            'earlier_start': '2032-01-01', 'start': '2032-02-01', 'end': '2032-03-31', 'horizon': '2032-05-31',
            'locations': [{'source': 'chat', 'container': 'desk', 'kind': 'channel'}],
            'import_files': [str(self.export)], 'allow_dms': False, 'allow_private_channels': False,
            'allow_attachments': False, 'retain_source_text': True, 'model_processing': 'selected_sources'}
        self.records = [{'id': 'chat:' + str(i), 'source': 'chat', 'container': 'desk', 'kind': 'channel',
            'date': '2032-02-03', 'author': 'Contributor 02', 'title': 'Desk note ' + str(i),
            'body': 'Contributor 02 repaired form ' + str(i) + '.', 'parent': None, 'links': [], 'attachments': []}
            for i in range(5)]

    def start(self):
        write_json(self.export, {'records': self.records, 'attachments': []})
        local_context.initialize(self.workspace, self.policy)
        local_context.import_export(self.workspace, self.export)

    @staticmethod
    def response(packet, folder, timeout):
        sections = []
        for s in packet['sections']:
            ids = [span['span_id'] for span in s['citation_spans']]
            sections.append({'section_id': s['section_id'], 'finding': 'Form repair was reported in ' + s['section_id'],
                'span_ids': ids, 'disposition': 'events' if ids else 'context',
                'events': [{'actor': 'Contributor 02', 'action': 'Repaired the intake form', 'state': 'completed',
                    'when': 'unknown', 'significance': 'Source reports a form repair, not verified adoption.', 'span_ids': ids}] if ids else [],
                'reason': '' if ids else 'This original body is entirely empty.'})
        return {'sections': sections, 'source_kinds': [{'record_id': r['id'], 'kind': r['source_kind'] or 'work'} for r in packet['records']]}

    def test_plan_is_local_and_local_only_blocks_calls(self):
        self.policy['model_processing'] = 'local_only'
        self.start()
        with patch.object(batches, 'model_call', side_effect=AssertionError('No transfer')):
            self.assertEqual(batches.plan(self.workspace)['remaining_batches'], 2)
            with self.assertRaises(ValueError): batches.run(self.workspace, 1)
        self.assertFalse((self.workspace / 'extraction-batches').exists())

    def test_bounded_resume_imports_same_journal_and_excludes_dm(self):
        self.records.append(self.records[0] | {'id': 'chat:excluded', 'kind': 'dm', 'body': 'EXCLUDED_BODY'})
        self.start()
        packets = []
        def invoke(packet, folder, timeout):
            packets.append(packet)
            return self.response(packet, folder, timeout)
        with patch.object(batches, 'model_call', side_effect=invoke):
            self.assertEqual(batches.run(self.workspace, 1)['pending_sections'], 1)
            self.assertEqual(batches.run(self.workspace, 1)['pending_sections'], 0)
            self.assertEqual(batches.run(self.workspace, 1)['model_calls'], 0)
        self.assertEqual(len(packets), 2)
        self.assertNotIn('EXCLUDED_BODY', json.dumps(packets))
        self.assertNotIn('chat:excluded', json.dumps(packets))
        _, _, _, source = batches.open_source(self.workspace)
        events = source.execute('episode_packet', {})['events']
        self.assertEqual(len(events), 5)
        self.assertEqual({e['actor'] for e in events}, {'Contributor 02'})
        self.assertTrue(all(e['span_ids'] for e in events))
        self.assertEqual(len(source.full_reads()), 5)
        self.assertFalse(source.execute('finish_check', {})['allowed'])

    def test_metadata_only_blocks_before_transfer(self):
        self.policy['retain_source_text'] = False
        self.start()
        with patch.object(batches, 'model_call') as invoke:
            with self.assertRaises(ValueError): batches.run(self.workspace, 1)
            invoke.assert_not_called()

    def test_duplicate_missing_extra_section_or_record_never_imports(self):
        self.start()
        _, _, corpus, source = batches.open_source(self.workspace)
        selected = list(batches.pending(corpus, source)['known'].values())[:4]
        packet = {'sections': selected, 'records': [r | {'source_kind': None} for r in self.records[:4]]}
        valid = self.response(packet, None, None)
        variants = [copy.deepcopy(valid) for _ in range(5)]
        variants[0]['sections'].pop()
        variants[1]['sections'][1] = variants[1]['sections'][0]
        variants[2]['sections'][0]['events'][0]['span_ids'] = ['chat:unselected@s0']
        variants[3]['source_kinds'][0]['record_id'] = 'chat:unselected'
        variants[4]['sections'][0]['events'][0]['state'] = 'proved'
        for response in variants:
            with self.subTest(response=response), self.assertRaises(ValueError):
                batches.validate_response(response, selected, corpus, source)

    def test_revocation_during_call_preserves_output_and_stops_before_import(self):
        self.start()
        def revoke(packet, folder, timeout):
            response = self.response(packet, folder, timeout)
            write_json(folder / 'output.json', response)
            write_json(self.workspace / 'policy.json', self.policy | {'model_processing': 'local_only'})
            return response
        with patch.object(batches, 'model_call', side_effect=revoke) as invoke:
            with self.assertRaises(ValueError): batches.run(self.workspace, 2)
            self.assertEqual(invoke.call_count, 1)
        self.assertTrue((self.workspace / 'extraction-batches/batch-0001/output.json').exists())
        journal = [json.loads(line) for line in (self.workspace / 'calls.jsonl').read_text().splitlines()]
        self.assertNotIn('save_extraction', [e['tool'] for e in journal])
        self.assertFalse((self.workspace / 'extraction-batches/running.lock').exists())

    def test_failure_is_not_retried_or_overwritten(self):
        self.start()
        with patch.object(batches, 'model_call', side_effect=ValueError('Model failed')) as invoke:
            with self.assertRaises(ValueError): batches.run(self.workspace, 3)
            with self.assertRaises(ValueError): batches.run(self.workspace, 3)
            self.assertEqual(invoke.call_count, 1)

    def test_changed_corpus_or_prompt_blocks_resume(self):
        self.start()
        with patch.object(batches, 'model_call', side_effect=self.response) as invoke:
            batches.run(self.workspace, 1)
            prompt = self.folder / 'new-prompt.md'
            prompt.write_text('Changed instructions', encoding='utf-8')
            with patch.object(batches, 'PROMPT', prompt), self.assertRaises(ValueError):
                batches.run(self.workspace, 1)
            corpus = read_json(self.workspace / 'corpus.json')
            corpus['records'][0]['body'] = 'Changed original'
            write_json(self.workspace / 'corpus.json', corpus)
            with self.assertRaises(ValueError): batches.run(self.workspace, 1)
            self.assertEqual(invoke.call_count, 1)

    def test_existing_host_is_blocked_while_batch_writer_holds_lock(self):
        self.start()
        workspace, _, corpus, scope, policy = local_context.load(self.workspace, for_model=True)
        host = LocalSheetSource(corpus, scope, workspace / 'calls.jsonl', policy)
        def invoke(packet, folder, timeout):
            self.assertEqual(host.execute('read_record', {'source': 'chat', 'id': 'chat:0'})['error'], 'extraction_in_progress')
            return self.response(packet, folder, timeout)
        with patch.object(batches, 'model_call', side_effect=invoke):
            batches.run(self.workspace, 1)
        self.assertEqual(host.execute('research_status', {})['error'], 'journal_changed')

    def test_timeout_and_unexpected_tools_are_preserved(self):
        for kind in ['timeout', 'tool']:
            with self.subTest(kind=kind):
                attempt = self.folder / kind
                attempt.mkdir()
                output = attempt / 'output.json'
                cmd = ['codex', '--cd', str(attempt), '-']
                if kind == 'timeout':
                    outcome = subprocess.TimeoutExpired(cmd, 30, output=b'{"type":"error"}\n', stderr=b'fictional transport timeout')
                else:
                    write_json(output, {'sections': []})
                    outcome = subprocess.CompletedProcess(cmd, 0, json.dumps({'type': 'item.started', 'item': {'type': 'command_execution'}}), '')
                with patch.object(batches, 'command', return_value=cmd), patch.object(batches.subprocess, 'run', side_effect=outcome if isinstance(outcome, Exception) else None, return_value=outcome):
                    with self.assertRaises(ValueError): batches.model_call({}, attempt, 30)
                receipt = read_json(attempt / 'receipt.json')
                self.assertIn('failure', receipt)
                self.assertTrue((attempt / 'input.json').exists())
                if kind == 'timeout':
                    self.assertIn('"type":"error"', (attempt / 'partial-stdout.txt').read_text())
                    self.assertEqual((attempt / 'diagnostic.txt').read_text(), 'fictional transport timeout')

    def test_private_runtime_home_controls_database_location(self):
        import model_backend
        runtime_home = self.folder / 'existing-codex-state'
        with patch.object(model_backend, 'executable', return_value=Path('codex')):
            cmd = model_backend.command(self.folder / 'output.json', self.folder / 'schema.json', runtime_home=runtime_home)
        options = [cmd[i + 1] for i, value in enumerate(cmd[:-1]) if value == '-c']
        self.assertIn('sqlite_home=' + json.dumps(str(runtime_home)), options)
        self.assertNotIn('sqlite_home=' + json.dumps(str(model_backend.ROOT / 'runs/model-workspace')), options)

    def test_empty_original_and_long_tail_survive(self):
        self.records = [self.records[0] | {'body': ''}, self.records[1] | {
            'body': ('A long source sentence carries background detail. ' * 70) + 'Contributor 02 repaired the final form.'}]
        self.start()
        packets = []
        def invoke(packet, folder, timeout):
            packets.append(packet)
            return self.response(packet, folder, timeout)
        with patch.object(batches, 'model_call', side_effect=invoke):
            result = batches.run(self.workspace, 3)
        self.assertEqual(result['pending_sections'], 0)
        self.assertIn('repaired the final form.', json.dumps(packets))
        _, _, _, source = batches.open_source(self.workspace)
        current = batches.pending(source.corpus, source)
        empty = next(s for s in current['saved'].values() if not s['span_ids'])
        self.assertEqual(empty['events'], [])
        self.assertEqual(empty['disposition'], 'context')

    def test_later_content_can_correct_provisional_record_kind(self):
        # Four long metadata-only spans precede the substantive template.
        headers = ['Capture field ' + str(i) + ': ' + ('background ' * 180) + '.' for i in range(4)]
        self.records = [self.records[0] | {'body': '\n'.join(headers) + '\nTemplate: require an owner and a review date.'}]
        self.start()
        kinds = iter(['discussion', 'work'])
        def invoke(packet, folder, timeout):
            response = self.response(packet, folder, timeout)
            kind = next(kinds)
            response['source_kinds'][0]['kind'] = kind
            return response
        with patch.object(batches, 'model_call', side_effect=invoke):
            first = batches.run(self.workspace, 1)
            self.assertGreater(first['pending_sections'], 0)
            second = batches.run(self.workspace, 1)
        self.assertEqual(second['pending_sections'], 0)
        _, _, _, source = batches.open_source(self.workspace)
        from ownership_server import saved_notes
        self.assertEqual(saved_notes(source.events)['chat:0']['source_kind'], 'work')
        saved = [e for e in source.events if e['tool'] == 'save_extraction']
        self.assertEqual(saved[0]['arguments']['source_kinds'][0]['kind'], 'discussion')
        self.assertEqual(saved[1]['arguments']['source_kinds'][0]['kind'], 'work')


if __name__ == '__main__':
    unittest.main()
