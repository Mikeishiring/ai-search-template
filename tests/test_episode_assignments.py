"""Bounded episode decisions preserve complete, current event coverage."""
import copy
import unittest

import test_narrative_retention as fixtures
import narrative_retention as retention
import depth_protocol as depth
from completion_server import spans
from ownership_review import evidence_version
from research_sheet_server import SheetSource


class EpisodeAssignmentTests(unittest.TestCase):
    setUp = fixtures.RetentionTests.setUp
    extraction = fixtures.RetentionTests.extraction
    extract_all = fixtures.RetentionTests.extract_all
    inventory = fixtures.RetentionTests.inventory

    def prepare(self, large=False):
        sections = self.extract_all()
        if large:
            # Repeated fictional events test transport and completeness only.
            first = self.extraction(sections[0], 0)
            first['events'] = [copy.deepcopy(first['events'][0]) for _ in range(1000)]
            self.assertTrue(self.server.execute('save_extraction', {'sections': [first]})['valid'])
        inventory = self.inventory()
        inventory['assignment_mode'] = 'saved'
        inventory['episodes'][0]['event_ids'] = []
        return sections, inventory

    def save_packet(self, packet, omit_last=False):
        rows = [{'event_id': e['event_id'], 'episode_id': 'return-workflow', 'exclusion_reason': ''}
                for e in packet['events']]
        if omit_last:
            rows.pop()
        result = self.server.execute('save_episode_assignments', {
            'retention_version': packet['retention_version'], 'assignments': rows})
        self.assertTrue(result['valid'], result)
        self.assertEqual(result['source_charge'], 0)
        return rows

    def assign_all(self):
        while True:
            packet = self.server.execute('episode_assignment_packet', {})
            if not packet['remaining']:
                return
            self.assertLessEqual(len(packet['events']), 30)
            self.save_packet(packet)

    def test_large_selection_requires_every_event_and_survives_restart(self):
        _, inventory = self.prepare(large=True)
        total = self.server.execute('episode_assignment_packet', {})['total']
        self.assertGreater(total, 1000)
        while True:
            packet = self.server.execute('episode_assignment_packet', {})
            if packet['remaining'] <= 30:
                self.save_packet(packet, omit_last=True)
                break
            self.save_packet(packet)
        self.assertFalse(self.server.execute('episode_inventory', inventory)['valid'])
        self.save_packet(self.server.execute('episode_assignment_packet', {}))
        result = self.server.execute('episode_inventory', inventory)
        self.assertTrue(result['valid'], result)
        restarted = SheetSource(self.corpus, self.scope, self.log)
        self.assertTrue(restarted.planning()['retention']['inventory_current'])
        self.assertEqual(restarted.execute('episode_assignment_packet', {})['remaining'], 0)
        page = restarted.execute('episode_packet', {})
        self.assertEqual(page['inventory']['hash'], result['inventory_hash'])
        self.assertNotIn('event_ids', page['inventory']['episodes'][0])

    def test_bad_assignments_do_not_hide_missing_events(self):
        self.prepare()
        packet = self.server.execute('episode_assignment_packet', {})
        row = {'event_id': packet['events'][0]['event_id'], 'episode_id': 'return-workflow', 'exclusion_reason': ''}
        for rows in ([row, row], [dict(row, event_id='unread:event')],
                     [dict(row, exclusion_reason='Unrelated material outside this personal episode.')],
                     [dict(row, episode_id='')], [dict(row, episode_id='../unsafe')],
                     [dict(row, episode_id='', exclusion_reason='Not useful')]):
            result = self.server.execute('save_episode_assignments', {
                'retention_version': packet['retention_version'], 'assignments': rows})
            self.assertFalse(result['valid'])
        self.assertEqual(self.server.execute('episode_assignment_packet', {})['remaining'], packet['total'])

    def test_changed_extraction_invalidates_assignments_and_selection(self):
        sections, inventory = self.prepare()
        packet = self.server.execute('episode_assignment_packet', {})
        rows = self.save_packet(packet)
        self.assertTrue(self.server.execute('episode_inventory', inventory)['valid'])
        item = self.extraction(sections[0], 0)
        item['events'][0]['when'] = 'Unknown event date; the minutes provide a recording date only.'
        self.assertTrue(self.server.execute('save_extraction', {'sections': [item]})['valid'])
        self.assertFalse(self.server.planning()['retention']['inventory_current'])
        rejected = self.server.execute('save_episode_assignments', {
            'retention_version': packet['retention_version'], 'assignments': rows})
        self.assertFalse(rejected['valid'])
        self.assertFalse(self.server.execute('episode_inventory', inventory)['valid'])

    def test_reassignment_invalidates_depth_until_inventory_is_resubmitted(self):
        _, inventory = self.prepare()
        packet = self.server.execute('episode_assignment_packet', {})
        rows = self.save_packet(packet)
        result = self.server.execute('episode_inventory', inventory)
        version = evidence_version([self.record], self.server.events)
        self.server.events += [
            {'sequence': len(self.server.events) + 1, 'source_charge': 0,
             'tool': 'sheet_plan', 'arguments': {'plan': {'accounts': [{'id': 'return-workflow'}]}},
             'result': {'valid': True, 'evidence_version': version, 'draft_hash': 'draft', 'plan_hash': 'plan'}},
            {'sequence': len(self.server.events) + 2, 'source_charge': 0,
             'tool': 'depth_review', 'arguments': {}, 'result': {'valid': True, 'evidence_version': version,
             'draft_hash': 'draft', 'plan_hash': 'plan', 'inventory_hash': result['inventory_hash']}}]
        self.assertIsNotNone(depth.current_review(self.server.events, version))
        rows[0].update(episode_id='', exclusion_reason='The committee furniture discussion adds context rather than a distinct workflow action.')
        self.assertTrue(self.server.execute('save_episode_assignments', {
            'retention_version': packet['retention_version'], 'assignments': rows})['valid'])
        self.assertIsNone(depth.current_review(self.server.events, version))
        self.assertFalse(self.server.planning()['retention']['inventory_current'])
        result2 = self.server.execute('episode_inventory', inventory)
        self.assertTrue(result2['valid'], result2)
        self.assertNotEqual(result['inventory_hash'], result2['inventory_hash'])
        self.assertIsNone(depth.current_review(self.server.events, version))

    def test_mixed_inline_unknown_and_empty_episodes_cannot_finalize(self):
        _, inventory = self.prepare()
        self.assign_all()
        changed = copy.deepcopy(inventory)
        changed['episodes'][0]['event_ids'] = [self.server.execute('episode_packet', {})['events'][0]['event_id']]
        self.assertFalse(self.server.execute('episode_inventory', changed)['valid'])
        changed = copy.deepcopy(inventory)
        changed['episodes'][0]['id'] = 'undeclared-workflow'
        self.assertFalse(self.server.execute('episode_inventory', changed)['valid'])
        changed = copy.deepcopy(inventory)
        empty = copy.deepcopy(changed['episodes'][0])
        empty.update(id='empty-episode', disposition='reserve', selection_reason='No evidence supports another independent workflow account here.')
        changed['episodes'].append(empty)
        self.assertFalse(self.server.execute('episode_inventory', changed)['valid'])

    def test_inline_inventory_becomes_provisional_when_new_assignments_begin(self):
        self.extract_all()
        self.assertTrue(self.server.execute('episode_inventory', self.inventory())['valid'])
        self.save_packet(self.server.execute('episode_assignment_packet', {}))
        self.assertFalse(self.server.planning()['retention']['inventory_current'])

    def test_packet_references_and_request_ceiling_remain_enforced(self):
        self.prepare()
        packet = self.server.execute('episode_assignment_packet', {})
        rows = self.save_packet(packet)
        recovered = self.server.execute('episode_assignment_packet', {'event_ids': [rows[0]['event_id']]})
        self.assertEqual(recovered['events'][0]['saved_assignment'], rows[0])
        self.assertIn('error', self.server.execute('episode_assignment_packet', {'event_ids': ['unread:event']}))
        self.server.request_limit = len(self.server.events)
        self.assertEqual(self.server.execute('save_episode_assignments', {
            'retention_version': packet['retention_version'], 'assignments': rows})['error'], 'request_limit_exhausted')

    def test_many_provisional_episode_names_do_not_expand_summary_or_errors(self):
        _, inventory = self.prepare(large=True)
        current = retention.state([self.record], self.server.events, spans)
        ids = list(current['events'])
        for start in range(0, len(ids), 100):
            rows = [{'event_id': eid, 'episode_id': 'candidate-%04d' % (start + i), 'exclusion_reason': ''}
                    for i, eid in enumerate(ids[start:start + 100])]
            self.assertTrue(self.server.execute('save_episode_assignments', {
                'retention_version': current['version'], 'assignments': rows})['valid'])
        packet = self.server.execute('episode_assignment_packet', {})
        self.assertEqual(packet['remaining'], 0)
        self.assertEqual(packet['episode_count'], len(ids))
        self.assertEqual(len(packet['episode_counts']), 80)
        self.assertTrue(packet['episode_counts_truncated'])
        result = self.server.execute('episode_inventory', inventory)
        self.assertFalse(result['valid'])
        self.assertEqual(result['errors'].count('Define every episode named in the saved assignments.'), 1)
        self.assertLess(len(result['errors']), 10)


if __name__ == '__main__':
    unittest.main()
