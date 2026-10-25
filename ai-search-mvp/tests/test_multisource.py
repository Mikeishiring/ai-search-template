"""Discovery across selected fictional channels; no network or disk database."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import SyntheticAdapter, SourceError
from engine import Runner


class MultiSourceTests(unittest.TestCase):
    def setUp(self):
        self.corpus = json.loads((ROOT / 'fixtures/multisource.corpus.json').read_text())
        self.scope = json.loads((ROOT / 'fixtures/multisource.scope.json').read_text())

    def run_case(self, scope=None, corpus=None, steps=1000):
        adapter = SyntheticAdapter(corpus or self.corpus, page_size=1)
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            runner = Runner(':memory:', adapter, scope or self.scope)
            try: result = runner.run(steps)
            finally: runner.close()
        return result, adapter.calls

    def test_followup_enumeration_finds_unlinked_records_across_six_locations(self):
        result, _ = self.run_case()
        expected = {r['id'] for r in self.corpus['records'] if r['source'] in self.scope['sources'] and r['date'] <= self.scope['horizon']}
        self.assertEqual({r['id'] for r in result['records']}, expected)
        self.assertEqual({r['source'] for r in result['records']}, set(self.scope['sources']))
        self.assertEqual(result['versions'], len(expected))
        self.assertTrue(all(c['requested_enumeration_window']['end'] == self.scope['horizon'] for c in result['coverage']))

    def test_supplied_alias_recovers_later_search_results_without_enumeration(self):
        corpus = copy.deepcopy(self.corpus)
        for source in corpus['sources']: source['enumeration'] = False
        baseline, _ = self.run_case(self.scope | {'aliases': [], 'include_followup_roots': False}, corpus)
        improved, calls = self.run_case(self.scope | {'include_followup_roots': False}, corpus)
        self.assertNotIn('email:later', {r['id'] for r in baseline['records']})
        self.assertIn('email:later', {r['id'] for r in improved['records']})
        self.assertTrue(any(c['operation'] == 'search_records' and c['args']['query'] == 'Harbor' for c in calls))
        self.assertTrue(all(c['retrieval_state'] == 'with_limits' for c in improved['coverage']))

    def test_unknown_followup_name_is_found_by_enumeration_not_a_guessed_alias(self):
        # Remove its later repost so there is no back-link through another record.
        corpus = copy.deepcopy(self.corpus)
        corpus['records'] = [r for r in corpus['records'] if r['id'] != 'email:repost']
        baseline, _ = self.run_case(self.scope | {'include_followup_roots': False}, corpus)
        improved, _ = self.run_case(corpus=corpus)
        self.assertNotIn('docs:unlinked', {r['id'] for r in baseline['records']})
        self.assertIn('docs:unlinked', {r['id'] for r in improved['records']})

    def test_exclusions_and_horizon_hold_despite_links_and_source_instructions(self):
        result, calls = self.run_case()
        self.assertFalse(any(c['source'] == 'chat-private' for c in calls))
        self.assertNotIn('private:discussion', {r['id'] for r in result['records']})
        self.assertNotIn('ops:future', {r['id'] for r in result['records']})
        self.assertEqual(result['outside_scope_links'], [{'origin': 'main:planning', 'source': 'chat-private', 'id': 'private:discussion', 'state': 'not_read_outside_selected_sources'}])
        self.assertFalse(any(c['operation'] in {'post_message', 'publish'} for c in calls))

    def test_alias_collision_never_merges_unconnected_work(self):
        result, _ = self.run_case()
        self.assertIn(['docs:collision'], result['components'])
        self.assertIn({'origin': 'email:repost', 'target': 'docs:unlinked', 'kind': 'reposts'}, result['edges'])

    def test_missing_attachment_and_budget_are_visible_limits(self):
        result, _ = self.run_case()
        self.assertTrue(any(t['operation'] == 'read_attachment' and t['state'] == 'blocked' for t in result['tasks']))
        self.assertEqual(next(c for c in result['coverage'] if c['source'] == 'chat-main')['retrieval_state'], 'with_limits')
        limited, _ = self.run_case(steps=3)
        self.assertEqual(limited['status'], 'budget_reached')
        self.assertTrue(any(t['state'] == 'pending' for t in limited['tasks']))
        self.assertTrue(all(c['semantic_reviews'] == 0 for c in result['coverage']))

    def test_new_scope_options_are_validated_before_any_read(self):
        for bad in [{'aliases': 'Harbor'}, {'aliases': ['']}, {'aliases': ['x'] * 11}, {'include_followup_roots': 'yes'}, {'horizon': '2029-01-01'}]:
            adapter = SyntheticAdapter(self.corpus)
            with self.assertRaises(ValueError): Runner(':memory:', adapter, self.scope | bad)
            self.assertEqual(adapter.calls, [])

    def test_old_scope_keeps_standalone_followups_opt_in(self):
        scope = {k: v for k, v in self.scope.items() if k not in {'aliases', 'include_followup_roots'}}
        result, calls = self.run_case(scope)
        self.assertFalse(any(c['operation'] == 'list_records' and c['args']['end'] > scope['end'] for c in calls))
        self.assertTrue(all(not c['standalone_followups_requested'] for c in result['coverage']))

    def test_failed_followup_window_cannot_report_enumeration_complete(self):
        boundary = self.scope['end']
        class PartialAdapter(SyntheticAdapter):
            def _dispatch(self, operation, source, args):
                if operation == 'list_records' and source == 'docs' and args['start'] == boundary:
                    raise SourceError('unavailable_or_hidden', 'Later window is unavailable')
                return super()._dispatch(operation, source, args)
        runner = Runner(':memory:', PartialAdapter(self.corpus), self.scope)
        try: result = runner.run()
        finally: runner.close()
        docs = next(c for c in result['coverage'] if c['source'] == 'docs')
        self.assertFalse(docs['enumeration_end'])
        self.assertEqual(docs['retrieval_state'], 'with_limits')


if __name__ == '__main__': unittest.main()
