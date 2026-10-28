"""Large coverage reviews retain completeness, exact roles and staleness gates."""
import copy
import unittest

import test_research_sheet as fixtures
import depth_coverage
import depth_protocol as depth
from research_sheet_server import SheetSource


class AttributionCoverageTests(unittest.TestCase):
    setUp = fixtures.ResearchSheetTests.setUp
    prepare = fixtures.ResearchSheetTests.prepare
    depth_audit = fixtures.ResearchSheetTests.depth_audit

    def planned(self, count=1):
        self.prepare()
        if count > 1:
            note = copy.deepcopy(next(e['arguments']['notes'][0] for e in self.server.events if e['tool'] == 'save_notes'))
            # Repeated fictional roles exercise the transport boundary only;
            # this fixture makes no claim of distinct real-world actions.
            note['attributions'] = [copy.deepcopy(note['attributions'][0]) for _ in range(count)]
            self.server.execute('save_notes', {'notes': [note]})
            self.assertTrue(self.server.execute('draft_check', {'draft': self.raw})['valid'])
        self.assertTrue(self.server.execute('sheet_plan', {'review': self.raw, 'plan': self.plan})['valid'])
        return self.depth_audit()

    def save_packet(self, packet, omit_last=False):
        rows = []
        for ref in packet['attributions']:
            i = ref['attribution_index']
            rows.append({'record_id': ref['record_id'], 'attribution_index': i,
                         'claim_ids': ref['referencing_claim_ids'],
                         'omission_reason': '' if ref['referencing_claim_ids'] else
                             'Repeated fictional role %d adds no separate form action.' % i})
        if omit_last:
            rows.pop()
        result = self.server.execute('save_attribution_coverage', {
            'review_version': packet['review_version'], 'attribution_coverage': rows})
        self.assertTrue(result['valid'], result)
        return rows

    def test_more_than_one_thousand_requires_the_final_row_and_survives_restart(self):
        audit = self.planned(1001)
        audit['attribution_coverage'] = []
        for _ in range(10):
            packet = self.server.execute('attribution_packet', {})
            self.assertEqual(len(packet['attributions']), 100)
            self.save_packet(packet)
        failed = self.server.execute('depth_review', audit)
        self.assertFalse(failed['valid'])
        self.assertIn('Account for every material actor/action, not only every source record.', failed['errors'])
        packet = self.server.execute('attribution_packet', {})
        self.assertEqual(packet['remaining'], 1)
        self.save_packet(packet)
        result = self.server.execute('depth_review', audit)
        self.assertTrue(result['valid'], result['errors'])
        self.assertEqual(result['attributions_accounted_for'], 1001)
        restarted = SheetSource(self.corpus, self.scope, self.log, retention_required=False)
        self.assertTrue(restarted.planning()['depth']['review_current'])
        self.assertEqual(restarted.execute('attribution_packet', {})['remaining'], 0)

    def test_duplicate_unknown_and_unrelated_claim_references_are_rejected(self):
        self.planned()
        packet = self.server.execute('attribution_packet', {})
        row = {'record_id': 'chat:one', 'attribution_index': 0, 'claim_ids': ['c1'], 'omission_reason': ''}
        for rows in ([row, row], [dict(row, attribution_index=5)], [dict(row, claim_ids=['unknown'])],
                     [dict(row, claim_ids=[])]):
            result = self.server.execute('save_attribution_coverage', {
                'review_version': packet['review_version'], 'attribution_coverage': rows})
            self.assertFalse(result['valid'])
        self.assertEqual(self.server.execute('attribution_packet', {})['remaining'], 1)

    def test_saved_and_inline_overlap_is_not_silently_deduplicated(self):
        audit = self.planned()
        self.save_packet(self.server.execute('attribution_packet', {}))
        result = self.server.execute('depth_review', audit)
        self.assertFalse(result['valid'])
        self.assertIn('Unknown or duplicate material attribution in depth review.', result['errors'])

    def test_changed_plan_refuses_stale_batch_and_requires_new_coverage(self):
        self.planned()
        old = self.server.execute('attribution_packet', {})
        rows = self.save_packet(old)
        plan = copy.deepcopy(self.plan)
        plan['accounts'][0]['title'] = 'The revised form account'
        self.assertTrue(self.server.execute('sheet_plan', {'review': self.raw, 'plan': plan})['valid'])
        result = self.server.execute('save_attribution_coverage', {
            'review_version': old['review_version'], 'attribution_coverage': rows})
        self.assertFalse(result['valid'])
        current = self.server.execute('attribution_packet', {})
        self.assertNotEqual(current['review_version'], old['review_version'])
        self.assertEqual(current['remaining'], 1)

    def test_coverage_revision_invalidates_a_previously_valid_review(self):
        audit = self.planned()
        rows = self.save_packet(self.server.execute('attribution_packet', {}))
        audit['attribution_coverage'] = []
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        self.assertTrue(self.server.planning()['depth']['review_current'])
        packet = self.server.execute('attribution_packet', {'refs': [{'record_id': 'chat:one', 'attribution_index': 0}]})
        self.assertEqual(packet['attributions'][0]['saved_review'], rows[0])
        rows[0]['omission_reason'] = 'The claim represents only this reported form action.'
        self.assertTrue(self.server.execute('save_attribution_coverage', {
            'review_version': packet['review_version'], 'attribution_coverage': rows})['valid'])
        self.assertFalse(self.server.planning()['depth']['review_current'])
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])

    def test_version_binds_evidence_draft_plan_and_inventory(self):
        self.planned()
        plan = depth.latest_plan(self.server.events)
        evidence = plan['result']['evidence_version']
        original, _ = depth_coverage.context(self.server.events, evidence, 'first-selection')
        changed, _ = depth_coverage.context(self.server.events, evidence, 'revised-selection')
        self.assertNotEqual(original, changed)
        for field in ('draft_hash', 'plan_hash'):
            events = copy.deepcopy(self.server.events)
            depth.latest_plan(events)['result'][field] = 'changed'
            changed, _ = depth_coverage.context(events, evidence, 'first-selection')
            self.assertNotEqual(original, changed)
        with self.assertRaises(ValueError):
            depth_coverage.context(self.server.events, 'changed-evidence', 'first-selection')

    def test_legacy_inline_review_still_works(self):
        audit = self.planned()
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        self.assertTrue(self.server.planning()['depth']['review_current'])

    def test_new_coverage_does_not_inherit_an_old_unfingerprinted_review(self):
        audit = self.planned()
        self.assertTrue(self.server.execute('depth_review', audit)['valid'])
        result = depth.latest_review(self.server.events)['result']
        for name in ('coverage_hash', 'coverage_review_version', 'coverage_batch_sequences'):
            result.pop(name)
        self.assertTrue(self.server.planning()['depth']['review_current'])
        self.save_packet(self.server.execute('attribution_packet', {}))
        self.assertFalse(self.server.planning()['depth']['review_current'])

    def test_cached_coverage_operations_still_obey_total_request_ceiling(self):
        self.planned()
        self.server.request_limit = len(self.server.events) + 1
        packet = self.server.execute('attribution_packet', {})
        self.assertEqual(packet['source_charge'], 0)
        count = len(self.server.events)
        result = self.server.execute('save_attribution_coverage', {
            'review_version': packet['review_version'],
            'attribution_coverage': [{'record_id': 'chat:one', 'attribution_index': 0,
                                     'claim_ids': ['c1'], 'omission_reason': ''}]})
        self.assertEqual(result['error'], 'request_limit_exhausted')
        self.assertEqual(len(self.server.events), count)


if __name__ == '__main__':
    unittest.main()
