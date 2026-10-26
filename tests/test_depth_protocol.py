"""Depth is enforced through real receipts, attribution accounting and stale-review checks."""
import copy
import json
import unittest
import test_research_sheet as fixtures
import depth_protocol as depth
from research_sheet_server import SheetSource
from research_sheet import ROOT, full_records, initialize, read_json, write_json, build
from ownership_server import saved_notes
from ownership_review import evidence_version
from completion_server import spans


class DepthProtocolTests(unittest.TestCase):
    setUp = fixtures.ResearchSheetTests.setUp
    prepare = fixtures.ResearchSheetTests.prepare
    depth_audit = fixtures.ResearchSheetTests.depth_audit

    def planned(self):
        self.prepare()
        self.assertTrue(self.server.execute('sheet_plan', {'review': self.raw, 'plan': self.plan})['valid'])

    def test_reading_everything_and_checked_prose_cannot_skip_depth_review(self):
        self.planned()
        result = self.server.execute('finish_check', {})
        self.assertFalse(result['allowed'])
        self.assertEqual(result['status'], 'review_depth')

    def test_record_citation_cannot_hide_an_unaccounted_contributor(self):
        self.planned()
        audit = self.depth_audit()
        audit['attribution_coverage'] = []
        result = self.server.execute('depth_review', audit)
        self.assertFalse(result['valid'])
        self.assertIn('Account for every material actor/action, not only every source record.', result['errors'])

    def test_original_storys_missing_proposal_is_a_real_attribution_gap(self):
        events = json.loads((ROOT / 'ai-search-mvp/runs/sheet/first-journal.json').read_text())
        plan = depth.latest_plan(events)['arguments']
        notes = saved_notes(events)
        roles = {(r['record_id'], r['attribution_index']): [] for c in plan['review']['claims'] for r in c['roles']}
        for claim in plan['review']['claims']:
            for ref in claim['roles']:
                roles[(ref['record_id'], ref['attribution_index'])].append(claim['id'])
        self.assertNotIn(('chat:origin', 0), roles)
        self.assertIn('proposed', notes['chat:origin']['attributions'][0]['action'])
        audit = {'accounts': [], 'attribution_coverage': [
            {'record_id': rid, 'attribution_index': i, 'claim_ids': ids, 'omission_reason': ''}
            for (rid, i), ids in roles.items()],
            'through_line': {'status': 'insufficient', 'account_ids': [], 'claim_ids': [],
                'interpretation': 'Original regression case.', 'exception_or_limit': 'No pattern assessment.'}}
        records = list(full_records(events).values())
        scope = json.loads((ROOT / 'ai-search-mvp/fixtures/sheet.scope.json').read_text())
        result = depth.validate_review(audit, events, records, notes, scope, evidence_version(records, events), spans)
        self.assertIn('Account for every material actor/action, not only every source record.', result['errors'])

    def test_checklist_cannot_use_fabricated_probes_or_unread_spans(self):
        self.planned()
        audit = self.depth_audit()
        audit['accounts'][0]['lenses'][0]['probe_sequences'] = [999]
        audit['accounts'][0]['lenses'][0]['evidence'][0]['span_id'] = 'invented'
        result = self.server.execute('depth_review', audit)
        self.assertFalse(result['valid'])
        self.assertTrue(any('probe receipts' in e for e in result['errors']))
        self.assertTrue(any('exact spans' in e for e in result['errors']))
        self.assertEqual(result['available_probe_receipts'][-1]['sequence'], self.server.events[-2]['sequence'])

    def test_probe_returns_its_real_journal_sequence_and_stays_correct_on_cache_hit(self):
        args = {'account_id': 'desk-form', 'lens': 'origins', 'question': 'Who proposed the form?',
                'source': 'chat', 'query': 'form'}
        for expected in [1, 2]:
            result = self.server.execute('research_probe', args)
            self.assertEqual(result['sequence'], expected)
        self.assertTrue(result['cache_hit'])
        restarted = SheetSource(self.corpus, self.scope, self.log)
        receipts = restarted.execute('research_status', {})['probe_receipts']
        self.assertEqual([p['sequence'] for p in receipts], [1, 2])

    def test_relabelling_cached_search_is_not_a_second_pass(self):
        self.planned()
        audit = self.depth_audit()
        # Keep the real post-draft event but change it to an earlier query.
        self.server.events.pop()
        result = self.server.execute('research_probe', {'account_id': 'desk-form', 'lens': 'contrary_evidence',
            'question': 'Can I count the same read twice?', 'source': 'chat', 'query': 'form'})
        self.assertTrue(result['cache_hit'])
        result = self.server.execute('depth_review', audit)
        self.assertFalse(result['valid'])
        self.assertTrue(any('new query' in e for e in result['errors']))

    def test_pending_research_blocks_finish_then_is_explicit_at_real_limit(self):
        self.planned()
        audit = self.depth_audit()
        audit['accounts'][0]['lenses'][0]['status'] = 'pending'
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        result = self.server.execute('finish_check', {})
        self.assertFalse(result['allowed'])
        self.assertEqual(result['status'], 'continue_depth')
        self.server.source_budget = self.server.source_calls()
        result = self.server.execute('finish_check', {})
        self.assertTrue(result['allowed'])
        self.assertEqual(result['status'], 'depth_budget_limit')
        self.assertEqual(len(result['unresolved']['depth_questions']), 1)

    def test_new_plan_invalidates_review_and_restart_preserves_gate(self):
        self.planned()
        audit = self.depth_audit()
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        restarted = SheetSource(self.corpus, self.scope, self.log)
        self.assertTrue(restarted.planning()['depth']['review_current'])
        plan = copy.deepcopy(self.plan)
        plan['accounts'][0]['title'] = 'Changed draft title'
        self.assertTrue(restarted.execute('sheet_plan', {'review': self.raw, 'plan': plan})['valid'])
        self.assertFalse(restarted.planning()['depth']['review_current'])
        self.assertFalse(restarted.execute('finish_check', {})['allowed'])

    def test_new_notes_invalidate_review(self):
        self.planned()
        audit = self.depth_audit()
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        note = copy.deepcopy(next(e for e in self.server.events if e['tool'] == 'save_notes')['arguments'])
        note['notes'][0]['finding'] += ' Additional interpretation.'
        self.server.execute('save_notes', note)
        self.assertFalse(self.server.planning()['depth']['review_current'])

    def test_one_episode_cannot_be_certified_as_a_career_pattern(self):
        self.planned()
        audit = self.depth_audit()
        audit['through_line']['status'] = 'pattern'
        result = self.server.execute('depth_review', audit)
        self.assertFalse(result['valid'])
        self.assertIn('One episode cannot establish a cross-episode pattern.', result['errors'])

    def test_sheet_capacity_is_ten_times_old_fixture_and_does_not_cut_off_at_45(self):
        self.assertEqual(self.server.source_budget, 450)
        self.assertEqual(self.server.request_limit, 800)
        for i in range(46):
            result = self.server.execute('search', {'source': 'chat', 'query': 'no-match-' + str(i)})
            self.assertNotIn('error', result)
        self.assertEqual(self.server.source_calls(), 46)
        self.assertEqual(result['remaining_calls'], 404)

    def test_new_build_cannot_bypass_depth_with_an_old_receipt_but_legacy_rebuilds(self):
        workspace = initialize(self.folder / 'legacy-check')
        events = json.loads((ROOT / 'ai-search-mvp/runs/sheet/first-journal.json').read_text())
        (workspace / 'calls.jsonl').write_text('\n'.join(json.dumps(e) for e in events) + '\n', encoding='utf-8')
        output = self.folder / 'rebuilt.html'
        with self.assertRaisesRegex(ValueError, 'requires a current depth review'):
            build(workspace, output)
        session = read_json(workspace / 'session.json')
        session.pop('depth_protocol')
        write_json(workspace / 'session.json', session)
        build(workspace, output)
        self.assertTrue(output.is_file())
        receipt = read_json(workspace / 'build-receipt.json')
        self.assertEqual(receipt['depth_protocol'], 'legacy; no enforced depth review')


if __name__ == '__main__':
    unittest.main()
