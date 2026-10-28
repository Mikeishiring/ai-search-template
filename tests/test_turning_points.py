import copy
from pathlib import Path
import tempfile
import unittest

import fictional_story as fixture
import turning_points
import depth_protocol as depth
from completion_server import spans
from research_sheet import build, read_json


class TurningPointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.workspace = fixture.initialize(self.folder)
        self.server = fixture.source(self.workspace)
        self.prepared = fixture.prepare(self.server)

    def test_reserve_handoff_is_reviewed_and_survives_finished_sheet(self):
        packet = self.server.execute('turning_point_packet', {})
        handoff = next(e for e in packet['events'] if e['record_id'] == 'docs:rota')
        self.assertEqual(handoff['origin']['disposition'], 'reserve')
        self.assertEqual(handoff['referencing_claim_ids'], [])
        self.assertFalse(self.server.execute('finish_check', {})['allowed'])
        fixture.complete(self.server, self.prepared)
        result = build(self.workspace, self.folder / 'story.html')
        self.assertEqual(result['accounts'], 1)
        packet = read_json(self.workspace / 'context.json')
        self.assertIn('I announced', packet['accounts'][0]['decisions'][0])
        self.assertIn('would take over', packet['accounts'][0]['decisions'][0])

    def test_unrelated_claim_stale_version_and_blanket_decisions_are_refused(self):
        packet = self.server.execute('turning_point_packet', {})
        rows = [{'event_id': e['event_id'], 'kind': 'handoff', 'account_id': 'calibration',
                 'importance': 'supporting', 'qualifying_event_ids': [],
                 'prose_checks': [{'claim_id': 'c1', 'quote': self.prepared[0]['claims'][0]['statement'],
                                  'state_check': 'The prose keeps the reported state of the original event.'}],
                 'claim_ids': ['c1'], 'reason': 'This event explains the current calibration work.'} for e in packet['events']]
        result = self.server.execute('save_turning_points', {'review_version': packet['review_version'], 'decisions': rows})
        self.assertFalse(result['valid'])
        self.assertTrue(any('every supporting event span' in e for e in result['errors']))
        row = dict(rows[0], kind='not_a_turning_point', account_id='', claim_ids=[])
        self.assertFalse(self.server.execute('save_turning_points', {'review_version': 'old', 'decisions': [row]})['valid'])
        self.assertEqual(self.server.execute('turning_point_packet', {})['remaining'], 2)

    def test_interruption_recovers_exact_draft_and_plan_without_source_charge(self):
        before = self.server.source_calls()
        restarted = fixture.source(self.workspace)
        packet = restarted.execute('resume_packet', {})
        self.assertEqual(packet['draft'], self.prepared[0])
        self.assertEqual(packet['checked_plan']['plan'], self.prepared[1])
        self.assertEqual(restarted.source_calls(), before)
        fixture.complete(restarted, self.prepared)

    def test_changed_narrative_invalidates_decisions_but_note_copy_does_not(self):
        ctx = turning_points.context(self.server.events, list(self.server.full_reads().values()), spans)
        events = copy.deepcopy(self.server.events)
        plan = depth.latest_plan(events)
        plan['arguments']['review']['coverage_notes'][0]['reason'] = 'More precise explanation of the same omitted announcement.'
        same = turning_points.context(events, list(self.server.full_reads().values()), spans)
        self.assertEqual(same['version'], ctx['version'])
        plan['arguments']['review']['claims'][0]['statement'] += ' A revised account.'
        changed = turning_points.context(events, list(self.server.full_reads().values()), spans)
        self.assertNotEqual(changed['version'], ctx['version'])

    def test_changed_turning_decision_invalidates_prior_depth_review(self):
        fixture.complete(self.server, self.prepared)
        events = copy.deepcopy(self.server.events[:-1])
        prior = depth.latest_review(events)
        saved = next(e for e in reversed(events) if e['tool'] == 'save_turning_points')
        update = copy.deepcopy(saved)
        update['arguments']['decisions'][0]['reason'] = 'A new interpretation requires another explicit depth review.'
        update['sequence'] = len(events) + 1
        events.append(update)
        self.assertIsNone(depth.current_review(events, prior['result']['evidence_version']))

    def completed_rows(self):
        fixture.complete(self.server, self.prepared)
        ctx = turning_points.context(self.server.events, list(self.server.full_reads().values()), spans)
        return ctx, copy.deepcopy(list(turning_points.saved(self.server.events, ctx['version']).values()))

    def test_essential_operating_choice_cannot_disappear_with_an_omission_reason(self):
        ctx, rows = self.completed_rows()
        rows[0].update(kind='operating_decision', claim_ids=[], prose_checks=[],
                       reason='Omit the practical choice so there is more room for the checklist implementation.')
        self.assertTrue(any('Essential events' in e for e in turning_points.validate(rows, ctx)))

    def test_citing_a_plan_cannot_pass_with_a_quote_missing_from_the_actual_prose(self):
        ctx, rows = self.completed_rows()
        handoff = next(r for r in rows if r['kind'] == 'handoff')
        handoff['prose_checks'][0]['quote'] = 'I completed the transfer of the night rota.'
        self.assertTrue(any('exact text' in e for e in turning_points.validate(rows, ctx)))

    def test_qualifying_event_must_survive_in_same_account(self):
        ctx, rows = self.completed_rows()
        rows[0]['qualifying_event_ids'] = [rows[1]['event_id']]
        rows[1].update(importance='supporting', claim_ids=[], prose_checks=[])
        saved = next(e for e in reversed(self.server.events) if e['tool'] == 'save_turning_points')
        saved['arguments']['decisions'] = rows
        result = turning_points.status(self.server.events, list(self.server.full_reads().values()), spans)
        self.assertFalse(result['current'])
        self.assertTrue(any('qualifying event' in e for e in result['errors']))

    def test_through_line_cannot_stay_only_in_research_notes(self):
        self.completed_rows()
        audit = copy.deepcopy(depth.latest_review(self.server.events)['arguments'])
        audit['through_line']['interpretation'] = 'I learned to make calibration work easier for other operators.'
        errors = turning_points.overview_errors(audit, depth.latest_plan(self.server.events))
        self.assertTrue(any('interpretation' in e for e in errors))

    def test_legacy_review_does_not_silently_gain_new_requirements(self):
        ctx, rows = self.completed_rows()
        ctx['protocol'] = turning_points.LEGACY_PROTOCOL
        for row in rows:
            for key in ('importance', 'prose_checks', 'qualifying_event_ids'):
                row.pop(key)
        self.assertEqual(turning_points.validate(rows, ctx), [])
