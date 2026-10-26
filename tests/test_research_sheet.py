"""Research-to-sheet boundaries, evidence preservation, gates and durable replay."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import research_sheet as bridge
import depth_protocol as depth
from research_sheet_server import SheetSource
from completion_server import spans


class ResearchSheetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.record = {'id': 'chat:one', 'source': 'chat', 'date': '2032-02-02',
            'author': 'Contributor 01', 'container': 'desk', 'title': 'Form completed',
            'body': 'I built the form. Contributor 02 owns the policy.',
            'parent': None, 'links': [], 'attachments': [], 'repost_of': None}
        self.corpus = {'synthetic': True, 'snapshot': '2032-06-01',
            'sources': [{'id': 'chat', 'platform': 'Fictional chat'}],
            'records': [self.record], 'attachments': []}
        self.scope = {'sources': ['chat'], 'subject': 'Contributor 01',
            'start': '2032-02-01', 'end': '2032-03-31', 'horizon': '2032-05-31'}
        self.log = self.folder / 'calls.jsonl'
        # These fixtures exercise the preserved pre-retention journal format.
        self.server = SheetSource(self.corpus, self.scope, self.log, retention_required=False)
        self.raw = {'claims': [{'id': 'c1', 'category': 'contribution',
            'statement': 'I built the form; Contributor 02 owns the policy.',
            'limits': 'Use and time savings are not established.',
            'evidence': [{'record_id': self.record['id'], 'span_id': s['span_id']} for s in spans(self.record)],
            'roles': [{'record_id': self.record['id'], 'attribution_index': 0}]}],
            'unknowns': ['Whether the form was used.'], 'rejected_conclusions': [],
            'stop_receipt_id': 'pending', 'research_choices': ['Read the original.'],
            'story_order': ['c1'], 'coverage_notes': []}
        account = {k: [] for k in bridge.FIELDS}
        account.update(id='desk-form', title='A shared form', period='February 2032',
                       summary=['c1'], contribution=['c1'], questions=['What changed after delivery?'])
        self.plan = {'overview': ['c1'], 'accounts': [account]}

    def prepare(self):
        for window in ['earlier', 'primary', 'followup']:
            self.server.execute('list_roots', {'source': 'chat', 'window': window})
        for lens, query in [('origins', 'form'), ('shared_ownership', 'policy')]:
            self.server.execute('research_probe', {'account_id': 'desk-form', 'lens': lens,
                'question': 'What does the selected record establish?', 'source': 'chat', 'query': query})
        self.server.execute('read_record', {'source': 'chat', 'id': 'chat:one'})
        selected = [s['span_id'] for s in spans(self.record)]
        result = self.server.execute('save_notes', {'notes': [{
            'record_id': 'chat:one', 'relevance': 'material', 'finding': self.record['body'],
            'span_ids': selected, 'source_kind': 'work',
            'attributions': [{'actor': 'Contributor 01', 'action': 'built the form',
                              'state': 'completed', 'span_ids': [selected[0]]}],
            'attribution_limits': 'Policy ownership is separate.'}]})
        self.assertNotIn('error', result)
        checked = self.server.execute('draft_check', {'draft': self.raw})
        self.assertTrue(checked['valid'], checked['errors'])

    def seal(self):
        self.prepare()
        planned = self.server.execute('sheet_plan', {'review': self.raw, 'plan': self.plan})
        self.assertTrue(planned['valid'], planned['errors'])
        audit = self.depth_audit()
        checked = self.server.execute('depth_review', audit)
        self.assertTrue(checked['valid'], checked['errors'])
        finished = self.server.execute('finish_check', {})
        self.assertTrue(finished['allowed'], finished)
        self.raw['stop_receipt_id'] = finished['receipt_id']

    def depth_audit(self):
        self.server.execute('research_probe', {'account_id': 'desk-form', 'lens': 'contrary_evidence',
            'question': 'Does the original establish use or a different owner?', 'source': 'chat', 'query': 'built'})
        evidence = [{'record_id': self.record['id'], 'span_id': s['span_id']} for s in spans(self.record)]
        return {'accounts': [{'account_id': 'desk-form', 'lenses': [
            {'lens': lens, 'status': 'limited', 'finding': 'The selected record reports a form and separate policy ownership.',
             'counterpoint': 'This single record does not establish the full episode.',
             'next_action': 'Review this gap with the person; no additional source is selected.',
             'evidence': evidence, 'claim_ids': ['c1'], 'probe_sequences': []} for lens in depth.LENSES]}],
            'attribution_coverage': [{'record_id': 'chat:one', 'attribution_index': 0, 'claim_ids': ['c1'], 'omission_reason': ''}],
            'through_line': {'status': 'single_episode', 'account_ids': ['desk-form'], 'claim_ids': ['c1'],
                             'interpretation': 'A single form-building episode.', 'exception_or_limit': 'No wider career pattern is established.'}}

    def test_compiled_sheet_retains_exact_evidence_limits_and_shared_credit(self):
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            self.seal()
            packet, check = bridge.compile_sheet(self.raw, self.plan, [self.record], self.server.events,
                                                 self.scope, self.corpus['snapshot'])
        self.assertTrue(check['valid'], check['errors'])
        self.assertEqual([s['content'] for s in packet['sources']], [s['quote'] for s in spans(self.record)])
        self.assertIn('Contributor 02 owns the policy.', packet['accounts'][0]['summary'])
        self.assertIn('Use and time savings are not established.', packet['accounts'][0]['summary'])
        self.assertEqual(packet['reviewStatus'], 'draft')
        path = self.folder / 'context.json'
        bridge.write_json(path, packet)
        output = self.folder / 'context.html'
        bridge.RENDERER.render(path, output)
        self.assertEqual(bridge.RENDERER.load_packet(output), packet)
        self.assertIn('Whether the form was used.', output.read_text(encoding='utf-8'))

    def test_finish_requires_research_notes_checked_draft_and_sheet_plan(self):
        self.assertFalse(self.server.execute('finish_check', {})['allowed'])
        self.prepare()
        result = self.server.execute('finish_check', {})
        self.assertFalse(result['allowed'])
        self.assertEqual(result['status'], 'plan_sheet')

    def test_sheet_cannot_drop_a_checked_claim_or_cite_an_unread_span(self):
        self.prepare()
        plan = copy.deepcopy(self.plan)
        plan['accounts'][0]['summary'] = []
        plan['accounts'][0]['contribution'] = []
        result = self.server.execute('sheet_plan', {'review': self.raw, 'plan': plan})
        self.assertFalse(result['valid'])
        raw = copy.deepcopy(self.raw)
        raw['claims'][0]['evidence'][0]['span_id'] = 'unread-span'
        result = self.server.execute('sheet_plan', {'review': raw, 'plan': self.plan})
        self.assertFalse(result['valid'])

    def test_changed_prose_requires_its_own_draft_check(self):
        self.prepare()
        raw = copy.deepcopy(self.raw)
        raw['claims'][0]['statement'] = 'I built everything.'
        result = self.server.execute('sheet_plan', {'review': raw, 'plan': self.plan})
        self.assertFalse(result['valid'])
        self.assertTrue(any('draft_check' in e for e in result['errors']))

    def test_restart_recovers_queue_notes_and_cache_without_new_source_charge(self):
        self.prepare()
        restarted = SheetSource(self.corpus, self.scope, self.log, retention_required=False)
        before = restarted.source_calls()
        packet = restarted.execute('writing_packet', {'ids': ['chat:one']})
        self.assertEqual(packet['records'][0]['note']['finding'], self.record['body'])
        reread = restarted.execute('read_record', {'source': 'chat', 'id': 'chat:one'})
        self.assertTrue(reread['cache_hit'])
        self.assertEqual(restarted.source_calls(), before)
        self.assertFalse(restarted.planning()['unfinished_window_sweeps'])

    def test_sealed_session_rejects_further_reads(self):
        self.seal()
        before = self.log.read_bytes()
        self.assertEqual(self.server.execute('source_inventory', {})['error'], 'session_sealed')
        self.assertEqual(before, self.log.read_bytes())

    def current_plan(self):
        plan = copy.deepcopy(self.plan)
        plan['schema'] = bridge.EXPORT_PROTOCOL
        plan['accounts'][0]['limits'] = []
        return plan

    def test_current_export_rejects_repeated_detail_but_permits_a_short_lead(self):
        self.prepare()
        plan = self.current_plan()
        plan['accounts'][0]['context'] = ['c1']
        packet, result = bridge.compile_sheet(self.raw, plan, [self.record], self.server.events,
                                              self.scope, self.corpus['snapshot'], draft=True)
        self.assertIsNone(packet)
        self.assertTrue(any('one field' in error for error in result['errors']))
        plan['accounts'][0]['context'] = []
        packet, result = bridge.compile_sheet(self.raw, plan, [self.record], self.server.events,
                                              self.scope, self.corpus['snapshot'], draft=True)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(packet['accounts'][0]['summary'], packet['accounts'][0]['contribution'])

    def test_new_claim_id_cannot_hide_identical_detail_prose(self):
        self.prepare()
        raw = copy.deepcopy(self.raw)
        raw['claims'].append(dict(copy.deepcopy(raw['claims'][0]), id='same-prose'))
        raw['story_order'].append('same-prose')
        plan = self.current_plan()
        plan['accounts'][0]['context'] = ['same-prose']
        packet, result = bridge.compile_sheet(raw, plan, [self.record], self.server.events,
                                              self.scope, self.corpus['snapshot'], draft=True)
        self.assertIsNone(packet)
        self.assertTrue(any('one field' in error for error in result['errors']))

    def test_current_export_keeps_audit_notes_private_and_capture_scope_once(self):
        self.prepare()
        plan = self.current_plan()
        scope = dict(self.scope, capture_limits=['Only the selected desk export was available.'])
        packet, result = bridge.compile_sheet(self.raw, plan, [self.record], self.server.events,
                                              scope, self.corpus['snapshot'], draft=True)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(packet['accounts'][0]['limits'], [])
        self.assertEqual(packet['accounts'][0]['questions'], plan['accounts'][0]['questions'])
        self.assertEqual(packet['person']['background'], scope['capture_limits'])
        self.assertNotIn(self.raw['unknowns'][0], json.dumps(packet))
        self.assertIn(self.raw['claims'][0]['limits'], packet['accounts'][0]['contribution'])

    def test_portable_limit_retains_its_own_original_excerpt(self):
        self.prepare()
        record = dict(self.record, id='docs:limit', source='docs', title='Trial measurement',
                      body='The trial did not collect turnaround measurements.')
        self.server.records[record['id']] = record
        self.server.scope['sources'].append('docs')
        self.server.execute('read_record', {'source': 'docs', 'id': record['id']})
        ids = [span['span_id'] for span in spans(record)]
        self.server.execute('save_notes', {'notes': [{
            'record_id': record['id'], 'relevance': 'material', 'finding': record['body'],
            'span_ids': ids, 'source_kind': 'evaluation', 'attributions': [],
            'attribution_limits': 'No outcome measurement is recorded.'}]})
        raw = copy.deepcopy(self.raw)
        raw['claims'].append({'id': 'c2', 'category': 'contribution', 'statement': record['body'],
                             'limits': '', 'roles': [],
                             'evidence': [{'record_id': record['id'], 'span_id': ids[0]}]})
        raw['story_order'].append('c2')
        plan = self.current_plan()
        plan['accounts'][0]['limits'] = ['c2']
        packet, result = bridge.compile_sheet(raw, plan, [self.record, record], self.server.events,
                                              self.scope, self.corpus['snapshot'], draft=True)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(packet['accounts'][0]['limits'], [record['body']])
        evidence = next(source for source in packet['sources'] if source['content'] == record['body'])
        self.assertIn(evidence['id'], packet['accounts'][0]['sourceRefs'])

    def test_current_session_schema_cannot_silently_accept_a_legacy_plan(self):
        self.prepare()
        current = SheetSource(self.corpus, self.scope, self.log, retention_required=False,
                              export_protocol=bridge.EXPORT_PROTOCOL)
        with self.assertRaises(ValueError):
            current.execute('sheet_plan', {'review': self.raw, 'plan': self.plan})
        result = current.execute('sheet_plan', {'review': self.raw, 'plan': self.current_plan()})
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(current.planning()['writing']['export_protocol'], bridge.EXPORT_PROTOCOL)

    def test_real_inputs_and_public_workspaces_never_enter_automated_demo(self):
        with self.assertRaises(ValueError): bridge.initialize(ROOT / 'private-test')
        workspace = bridge.initialize(self.folder / 'research')
        data = bridge.read_json(workspace / 'session.json')
        data['scope']['subject'] = 'Changed subject'
        bridge.write_json(workspace / 'session.json', data)
        with self.assertRaises(ValueError): bridge.load_session(workspace)
        data['synthetic'] = False
        bridge.write_json(workspace / 'session.json', data)
        with self.assertRaises(ValueError): bridge.load_session(workspace)

    def test_excluded_and_future_records_cannot_be_read(self):
        corpus = bridge.read_json(bridge.EXPERIMENTS / 'fixtures/sheet.corpus.json')
        scope = bridge.read_json(bridge.EXPERIMENTS / 'fixtures/sheet.scope.json')
        server = SheetSource(corpus, scope, self.log)
        self.assertEqual([s['id'] for s in server.execute('source_inventory', {})['sources']], scope['sources'])
        with self.assertRaises(ValueError):
            server.execute('read_record', {'source': 'private', 'id': 'private:excluded'})
        self.assertIn('error', server.execute('read_record', {'source': 'chat', 'id': 'chat:future'}))
        server.execute('read_record', {'source': 'chat', 'id': 'chat:decision'})
        self.assertEqual(server.planning()['outside_scope_links'], [{'source': 'private', 'id': 'private:excluded'}])
        self.assertNotIn('private:excluded', server.full_reads())


if __name__ == '__main__':
    unittest.main()
