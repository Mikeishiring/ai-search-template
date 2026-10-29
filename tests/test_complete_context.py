"""Preservation and freshness across the complete career document."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('complete_example', ROOT / 'tools/build_complete_example.py')
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)
renderer = example.renderer
merge = renderer.load_helper('merge_notebook')
notebook = renderer.load_helper('render_notebook')
archive = renderer.load_helper('archive_context')


class CompleteContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = example.example()

    def source(self, packet=None):
        path = self.root / 'context.json'
        path.write_text(json.dumps(packet or self.packet), encoding='utf-8')
        return path

    def refresh(self):
        self.packet['interview']['contextSha256'] = renderer.sections.evidence_fingerprint(self.packet)

    def test_all_views_roundtrip_in_one_file(self):
        output, rebuilt = self.root / 'complete.html', self.root / 'rebuilt.html'
        renderer.render(self.source(), output)
        self.assertEqual(renderer.load_packet(output), self.packet)
        renderer.render(output, rebuilt)
        self.assertEqual(output.read_bytes(), rebuilt.read_bytes())
        text = output.read_text(encoding='utf-8')
        for key in ['work', 'timeline', 'interview']:
            self.assertIn('id="' + key + '"', text)
        for period in self.packet['timeline']:
            self.assertIn('id="quarter-' + period['id'] + '"', text)
        for story in self.packet['interview']['stories']:
            self.assertIn('id="prep-story-' + story['id'] + '"', text)

    def test_timeline_only_evidence_is_retained_and_references_are_checked(self):
        source = dict(self.packet['sources'][0], id='timeline-only')
        self.packet['sources'].append(source)
        self.packet['timeline'][0]['sourceRefs'].append(source['id'])
        self.refresh(); renderer.validate(self.packet)
        self.packet['timeline'][0]['accountIds'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'accountIds'):
            renderer.validate(self.packet)

    def test_changed_evidence_cannot_silently_reuse_stale_preparation(self):
        output = self.root / 'complete.html'; output.write_text('Keep this revision')
        self.packet['accounts'][0]['outcome'] = 'Corrected outcome'
        with self.assertRaisesRegex(ValueError, 'context changed'):
            renderer.render(self.source(), output)
        self.assertEqual(output.read_text(), 'Keep this revision')

    def test_rehearsal_and_presentation_do_not_change_evidence_fingerprint(self):
        basis = renderer.sections.evidence_fingerprint(self.packet)
        story = self.packet['interview']['stories'][0]['id']
        self.packet['rehearsal'] = {'updatedAt': 10, 'notes': {story: 'Ask about the later outcome.'}}
        self.packet['presentation'] = {'headline': 'A new visual title'}
        self.assertEqual(renderer.sections.evidence_fingerprint(self.packet), basis)
        renderer.validate(self.packet)
        output = self.root / 'complete.html'; renderer.render(self.source(), output)
        self.assertEqual(renderer.load_packet(output)['rehearsal'], self.packet['rehearsal'])
        self.packet['rehearsal']['notes']['missing-story'] = 'Invalid'
        with self.assertRaisesRegex(ValueError, 'Rehearsal'):
            renderer.validate(self.packet)

    def test_section_content_is_inert_and_escaped(self):
        hostile = '</script><img src=x onerror=alert(1)>'
        self.packet['timeline'][0]['title'] = hostile
        self.packet['interview']['questions'][0]['answer'] = hostile
        self.refresh()
        output = self.root / 'complete.html'; renderer.render(self.source(), output)
        self.assertNotIn(hostile, output.read_text(encoding='utf-8'))
        self.assertEqual(renderer.load_packet(output), self.packet)

    def test_archive_recovery_keeps_all_views_and_notes(self):
        key = self.packet['interview']['stories'][0]['id']
        self.packet['rehearsal'] = {'updatedAt': 10, 'notes': {key: 'Private practice detail'}}
        result = archive.build(self.source(), self.root / 'archive')
        output = self.root / 'recovered.html'
        archive.export(Path(result['database']), output)
        self.assertEqual(renderer.load_packet(output), self.packet)

    def test_work_only_update_cannot_remove_views_from_file_or_archive(self):
        source = self.source()
        output = self.root / 'complete.html'; renderer.render(source, output)
        result = archive.build(source, self.root / 'archive')
        original = output.read_bytes()
        basic = {k: v for k, v in self.packet.items() if k not in ['timeline', 'interview']}
        self.source(basic)
        with self.assertRaisesRegex(ValueError, 'would remove'):
            renderer.render(source, output)
        with self.assertRaisesRegex(ValueError, 'would remove'):
            archive.build(source, self.root / 'archive', update=True)
        self.assertEqual(output.read_bytes(), original)
        self.assertEqual(Path(result['path']).read_bytes(), original)
        renderer.render(source, output, allow_view_removal=True)
        self.assertNotIn('interview', renderer.load_packet(output))

    def test_legacy_notebook_cannot_replace_complete_document(self):
        with self.assertRaisesRegex(ValueError, 'complete career document'):
            notebook.render(self.source(), self.root / 'older.html')

    def test_notebook_reconciliation_preserves_new_capabilities_and_old_writing(self):
        base = {k: v for k, v in self.packet.items() if k not in ['timeline', 'interview']}
        quarters = json.loads((ROOT / 'examples/notebook-quarters.json').read_text())
        draft = notebook.draft_from_packet(base, {}, quarters)
        draft['accounts'][0]['practice'] = 'Keep my saved rehearsal guidance.'
        draft['accounts'][0]['choice'] = 'An edited decision that needs reconciliation.'
        added = copy.deepcopy(draft['accounts'][0]); added['id'] = 'older-unique-story'
        draft['accounts'].append(added)
        merged = merge.merge(base, draft)
        for old in base['accounts']:
            new = next(a for a in merged['accounts'] if a['id'] == old['id'])
            for field, value in old.items():
                if field != 'sourceRefs': self.assertEqual(new[field], value)
        self.assertIn('older-unique-story', {a['id'] for a in merged['accounts']})
        self.assertEqual(len(merged['timeline']), len(quarters['quarters']))
        self.assertIn('An edited decision', json.dumps(merged['sources']))
        self.assertEqual(merged['interview']['stories'][0]['practice'], 'Keep my saved rehearsal guidance.')
        with self.assertRaisesRegex(ValueError, 'already has interview'):
            merge.merge(merged, draft)

    def test_public_complete_example_is_reproducible(self):
        self.assertEqual(self.packet, json.loads((ROOT / 'examples/complete-context.json').read_text()))
        output = self.root / 'demo.html'; renderer.render(self.source(), output)
        self.assertEqual(output.read_bytes(), (ROOT / 'CAREER-CONTEXT.html').read_bytes())


if __name__ == '__main__': unittest.main()
