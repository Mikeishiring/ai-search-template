"""Regression cases for lost late evidence, discarded episodes and honest completion."""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import narrative_retention as retention
from research_sheet_server import SheetSource
from ownership_server import saved_notes
from ownership_review import evidence_version
import depth_protocol as depth
from completion_server import spans
from research_sheet import initialize, load_session


class RetentionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.record = {'id':'docs:minutes', 'source':'docs', 'date':'2033-02-10', 'author':'Contributor 02',
            'title':'Weekly minutes', 'container':'library', 'parent':None, 'links':[], 'attachments':[],
            'body': ('The committee discussed furniture and room schedules for the coming season. ' * 28)
                    + 'Contributor 01 changed the return workflow after a volunteer found an access error.'}
        self.scope = {'subject':'Contributor 01', 'sources':['docs'], 'start':'2033-02-01',
                      'end':'2033-03-31', 'horizon':'2033-06-01'}
        self.corpus = {'synthetic':True, 'snapshot':'2033-06-01', 'sources':[{'id':'docs','platform':'Fictional records'}],
                       'records':[self.record], 'attachments':[]}
        self.log = Path(self.temp.name)/'calls.jsonl'
        self.server = SheetSource(self.corpus,self.scope,self.log)
        self.server.execute('read_record',{'source':'docs','id':self.record['id']})

    def extraction(self, section, i):
        refs=[s['span_id'] for s in section['citation_spans']]
        return {'section_id':section['section_id'], 'finding':f'Section {i} records committee discussion and the available workflow evidence.',
                'span_ids':refs,'disposition':'events','reason':'',
                'events':[{'actor':'Contributor 01','action':'changed the library return workflow',
                           'state':'reported','when':'2033-02-10, as recorded in the minutes',
                           'significance':'The change responds to a reported access problem.', 'span_ids':[refs[-1]]}]}

    def extract_all(self):
        sections=self.server.execute('extraction_packet',{})['sections']
        result=self.server.execute('save_extraction',{'sections':[self.extraction(s,i) for i,s in enumerate(sections)]})
        self.assertTrue(result['valid'],result)
        return sections

    def inventory(self):
        events=self.server.execute('episode_packet',{})['events']
        return {'episodes':[{'id':'return-workflow','title':'Repairing the return workflow',
            'event_ids':[e['event_id'] for e in events], 'why_interesting':'A volunteer report led to an explicit workflow correction.',
            'disposition':'selected','selection_reason':'The episode includes a concrete response to an access problem.'}],
            'excluded_events':[], 'challenge':{'reserve_episode_id':'','selected_episode_id':'','comparison':'',
                'no_reserve_reason':'Only this workflow episode is established by the selected minutes.'}}

    def test_late_section_survives_and_header_only_note_cannot_finish(self):
        packet=self.server.execute('extraction_packet',{})
        self.assertGreater(len(packet['sections']),1)
        self.assertIn('access error',packet['sections'][-1]['citation_spans'][-1]['quote'])
        first=self.extraction(packet['sections'][0],0)
        self.assertTrue(self.server.execute('save_extraction',{'sections':[first]})['valid'])
        self.assertNotIn(self.record['id'],saved_notes(self.server.events))
        self.assertEqual(self.server.execute('finish_check',{})['status'],'retain_evidence')
        self.assertFalse(self.server.execute('episode_inventory',self.inventory())['valid'])

    def test_original_bland_notes_and_header_copies_are_refused(self):
        self.assertEqual(self.server.execute('save_notes',{'notes':[]})['error'],'section_extraction_required')
        section=self.server.execute('extraction_packet',{})['sections'][0]
        for finding in ['Reviewed during full archive sweep; no distinct episode.', 'THREAD PARENT MESSAGE From user Time today']:
            item=self.extraction(section,0);item['finding']=finding
            self.assertFalse(self.server.execute('save_extraction',{'sections':[item]})['valid'])

    def test_cross_section_evidence_and_generic_participation_are_refused(self):
        sections=self.server.execute('extraction_packet',{})['sections']
        item=self.extraction(sections[0],0)
        item['events'][0]['span_ids']=[sections[-1]['citation_spans'][-1]['span_id']]
        self.assertFalse(self.server.execute('save_extraction',{'sections':[item]})['valid'])
        item=self.extraction(sections[0],0);item['events'][0]['action']='Documented or participated in this source-specific event'
        self.assertFalse(self.server.execute('save_extraction',{'sections':[item]})['valid'])

    def test_repeat_generic_context_cannot_discard_two_sections(self):
        sections=self.server.execute('extraction_packet',{})['sections']
        items=[self.extraction(s,i) for i,s in enumerate(sections)]
        for item in items:
            item.update(finding='Committee business provides context for this specific document.',events=[],
                        disposition='context',reason='This section describes room planning without a personal contribution.')
        self.assertFalse(self.server.execute('save_extraction',{'sections':items})['valid'])

    def test_derived_notes_and_events_survive_restart_without_source_access(self):
        self.extract_all();before=self.server.source_calls()
        restarted=SheetSource(self.corpus,self.scope,self.log)
        result=restarted.execute('episode_packet',{})
        self.assertTrue(result['events'])
        self.assertEqual(restarted.source_calls(),before)
        self.assertIn(self.record['id'],saved_notes(restarted.events))
        self.assertEqual(restarted.planning()['retention']['pending_sections'],0)

    def test_inventory_cannot_drop_events_or_use_blanket_exclusion(self):
        self.extract_all();inventory=self.inventory()
        current=retention.state([self.record],self.server.events,spans)
        self.assertTrue(retention.validate_inventory(inventory,current)['valid'])
        inventory['episodes'][0]['event_ids'].pop()
        self.assertFalse(retention.validate_inventory(inventory,current)['valid'])

    def test_inventory_and_later_challenge_are_required_and_stale_after_change(self):
        sections=self.extract_all();inventory=self.inventory()
        result=self.server.execute('episode_inventory',inventory);self.assertTrue(result['valid'])
        plan={'accounts':[{'id':'return-workflow'}]}
        self.assertEqual(retention.plan_errors(plan,[self.record],self.server.events,spans),[])
        self.assertTrue(retention.plan_errors(plan,[self.record],self.server.events,spans,challenged=True))
        # A preserved plan receipt marks the chronological challenge boundary.
        self.server.events.append({'sequence':len(self.server.events)+1,'tool':'sheet_plan',
                                   'arguments':{'plan':plan},'result':{'valid':True}})
        event={'sequence':len(self.server.events)+1,'tool':'episode_inventory','arguments':inventory,'result':result}
        self.server.events.append(event)
        self.assertEqual(retention.plan_errors(plan,[self.record],self.server.events,spans,challenged=True),[])
        replacement=self.extraction(sections[0],0);replacement['finding']='The committee scheduled room preparation before the return-workflow discussion.'
        self.server.events.append({'tool':'save_extraction','arguments':{'sections':[replacement]},'result':{'valid':True}})
        self.assertTrue(retention.plan_errors(plan,[self.record],self.server.events,spans))

    def test_unknown_unread_sections_and_foreign_fixture_are_refused(self):
        self.assertIn('error',self.server.execute('extraction_packet',{'section_ids':['private:unread#section']}))
        with self.assertRaises(ValueError):initialize(Path(self.temp.name)/'bad','../private')
        workspace=initialize(Path(self.temp.name)/'good','story-depth')
        self.assertEqual(load_session(workspace)[1]['retention_protocol'],retention.PROTOCOL)

    def test_event_date_and_significance_invalidate_evidence_even_when_notes_are_unchanged(self):
        sections=self.extract_all()
        before=evidence_version([self.record],self.server.events)
        notes=copy.deepcopy(saved_notes(self.server.events))
        replacement=self.extraction(sections[0],0)
        replacement['events'][0]['when']='Unknown event date; the minutes date is a recording date.'
        replacement['events'][0]['significance']='The date remains uncertain despite the recorded action.'
        self.assertTrue(self.server.execute('save_extraction',{'sections':[replacement]})['valid'])
        self.assertEqual(saved_notes(self.server.events),notes)
        self.assertNotEqual(evidence_version([self.record],self.server.events),before)

    def test_changed_inventory_challenge_invalidates_depth_review(self):
        self.extract_all();inventory=self.inventory()
        result=self.server.execute('episode_inventory',inventory)
        version=evidence_version([self.record],self.server.events)
        self.server.events += [
            {'tool':'sheet_plan','arguments':{'plan':{'accounts':[{'id':'return-workflow'}]}},
             'result':{'valid':True,'evidence_version':version,'draft_hash':'draft','plan_hash':'plan'}},
            {'tool':'depth_review','result':{'valid':True,'evidence_version':version,'draft_hash':'draft',
              'plan_hash':'plan','inventory_hash':retention.digest(inventory)}}]
        self.assertIsNotNone(depth.current_review(self.server.events,version))
        changed=copy.deepcopy(inventory);changed['challenge']['no_reserve_reason']='The supplied scope includes no second work episode or alternative sequence.'
        self.server.events.append({'tool':'episode_inventory','arguments':changed,'result':result})
        self.assertIsNone(depth.current_review(self.server.events,version))

    def test_short_concrete_actions_do_not_force_compound_event_summaries(self):
        item=self.extraction(self.server.execute('extraction_packet',{})['sections'][0],0)
        item['events'][0]['action']='implemented catalogue adapter'
        item['events'][0]['significance']='Shared implementation contribution'
        self.assertTrue(self.server.execute('save_extraction',{'sections':[item]})['valid'])

    def test_context_reason_revision_changes_evidence_version(self):
        sections=self.extract_all()
        replacement=self.extraction(sections[0],0)
        replacement.update(disposition='context',events=[],reason='The facilities discussion does not assign work to the subject.')
        self.assertTrue(self.server.execute('save_extraction',{'sections':[replacement]})['valid'])
        before=evidence_version([self.record],self.server.events)
        replacement['reason']='The committee schedule is contextual; its decisions belong to a different team.'
        self.assertTrue(self.server.execute('save_extraction',{'sections':[replacement]})['valid'])
        self.assertNotEqual(evidence_version([self.record],self.server.events),before)

    def test_legacy_evidence_digest_remains_byte_for_byte_compatible(self):
        from ownership_review import digest
        self.assertEqual(evidence_version([self.record],self.server.events),
                         digest([[self.record],saved_notes(self.server.events)]))


if __name__=='__main__':unittest.main()
