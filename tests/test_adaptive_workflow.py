"""Full extracted-skill journeys and failure/recovery boundaries."""
import copy
from contextlib import closing
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from career_fixtures import CASES, context, resume

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tools import build_skill


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'skills/career-context-sheet/scripts' / (name + '.py'))
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


archive = module('archive_context')
renderer = module('render_context')
resume_renderer = module('render_resume')


class AdaptiveWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / 'context.json'
        self.workspace = self.folder / 'workspace'
        self.packet = context('engineering')
        self.save()

    def save(self):
        self.source.write_text(json.dumps(self.packet), encoding='utf-8')

    def test_extracted_skill_six_disciplines_build_search_resume_and_recover(self):
        bundle = self.folder / 'skill.zip'
        build_skill.build(bundle)
        with zipfile.ZipFile(bundle) as zipped:
            zipped.extractall(self.folder / 'isolated')
        scripts = self.folder / 'isolated/career-context-sheet/scripts'

        def command(script, *args):
            result = subprocess.run([sys.executable, '-I', str(scripts / script), *map(str, args)],
                                    cwd=self.folder, capture_output=True, text=True, timeout=20)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout)

        for role in CASES:
            with self.subTest(role=role):
                self.packet = context(role)
                self.save()
                workspace = self.folder / role
                built = command('archive_context.py', 'build', self.source, workspace)
                database, sheet = workspace / 'career.sqlite', workspace / 'CAREER-CONTEXT.html'
                stored = renderer.load_packet(sheet)
                self.assertEqual(stored, self.packet)
                results = command('archive_context.py', 'search', database, self.packet['accounts'][0]['title'])
                self.assertTrue(any(r['id'] == role for r in results))
                inspected = command('render_resume.py', sheet, '--inspect')
                projection = self.folder / 'resume.json'
                projection.write_text(json.dumps(resume(self.packet, inspected['contextSha256'])), encoding='utf-8')
                output = workspace / 'RESUME.html'
                command('render_resume.py', sheet, projection, output)
                raw = output.read_text(encoding='utf-8')
                self.assertIn(self.packet['accounts'][0]['sharedCredit'], raw)
                self.assertIn(self.packet['accounts'][0]['limits'][0], raw)
                self.assertIn(self.packet['profile']['targetRoles'][0], raw)
                self.assertTrue(command('archive_context.py', 'build', sheet, workspace, '--update')['newRevision'] is False)
                recovered = workspace / 'recovered.html'
                command('archive_context.py', 'export', database, recovered)
                self.assertEqual(recovered.read_bytes(), sheet.read_bytes())
                self.assertEqual(hashlib.sha256(recovered.read_bytes()).hexdigest(), built['revision'])

    def test_corrections_are_searchable_and_previous_revision_recovers(self):
        first = archive.build(self.source, self.workspace)
        old = (self.workspace / 'CAREER-CONTEXT.html').read_bytes()
        self.packet['accounts'][0]['outcome'] = 'Correction: the change was reverted.'
        self.packet['sources'][0]['content'] += ' Correction: the change was reverted.'
        self.packet['reviewStatus'] = 'draft'
        self.save()
        archive.build(self.source, self.workspace, update=True)
        db = self.workspace / 'career.sqlite'
        self.assertTrue(archive.search(db, 'reverted'))
        with closing(sqlite3.connect(db)) as connection:
            self.assertEqual(connection.execute('SELECT count(*) FROM revisions').fetchone()[0], 2)
            self.assertEqual(connection.execute('PRAGMA foreign_key_check').fetchall(), [])
        recovered = self.folder / 'old.html'
        archive.export(db, recovered, first['revision'])
        self.assertEqual(recovered.read_bytes(), old)

    def test_invalid_update_and_foreign_person_preserve_archive(self):
        archive.build(self.source, self.workspace)
        before = (self.workspace / 'career.sqlite').read_bytes()
        self.packet['person']['name'] = 'Different person'
        self.save()
        with self.assertRaisesRegex(ValueError, 'different person'):
            archive.build(self.source, self.workspace, update=True)
        self.assertEqual(before, (self.workspace / 'career.sqlite').read_bytes())
        self.packet['accounts'][0]['sourceRefs'] = ['missing']
        self.save()
        with self.assertRaises(ValueError):
            archive.build(self.source, self.workspace, update=True)
        self.assertEqual(before, (self.workspace / 'career.sqlite').read_bytes())

    def test_html_edits_and_unknown_database_are_not_overwritten(self):
        archive.build(self.source, self.workspace)
        sheet = self.workspace / 'CAREER-CONTEXT.html'
        sheet.write_text('Independent correction', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'local changes'):
            archive.build(self.source, self.workspace, update=True)
        self.assertEqual(sheet.read_text(), 'Independent correction')
        foreign = self.folder / 'foreign.sqlite'
        with closing(sqlite3.connect(foreign)) as db:
            db.execute('CREATE TABLE private (text)')
        with self.assertRaisesRegex(ValueError, 'supported career-context'):
            archive.search(foreign, 'anything')

    def test_failed_sheet_write_rolls_back_new_revision(self):
        archive.build(self.source, self.workspace)
        before = (self.workspace / 'career.sqlite').read_bytes()
        self.packet['accounts'][0]['outcome'] = 'An updated result'
        self.save()
        with patch.object(archive, 'atomic_write', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                archive.build(self.source, self.workspace, update=True)
        self.assertEqual(before, (self.workspace / 'career.sqlite').read_bytes())

    def test_failed_database_initialization_can_be_retried(self):
        original_connect = sqlite3.connect
        class FailingConnection(sqlite3.Connection):
            def executescript(self, sql):
                raise sqlite3.OperationalError('disk full during schema creation')
        with patch.object(archive.sqlite3, 'connect', side_effect=lambda *a, **kw: original_connect(*a, **kw, factory=FailingConnection)):
            with self.assertRaises(sqlite3.OperationalError):
                archive.build(self.source, self.workspace)
        self.assertFalse((self.workspace / 'career.sqlite').exists())
        self.assertFalse((self.workspace / 'CAREER-CONTEXT.html').exists())
        self.assertTrue(archive.build(self.source, self.workspace)['newRevision'])

    def test_resume_rejects_stale_and_unresolved_evidence_preserving_output(self):
        fingerprint = hashlib.sha256(self.source.read_bytes()).hexdigest()
        projection = resume(self.packet, fingerprint)
        draft = self.folder / 'resume.json'
        output = self.folder / 'resume.html'
        output.write_text('Keep this resume', encoding='utf-8')
        for mutation in ['stale', 'missing']:
            broken = copy.deepcopy(projection)
            if mutation == 'stale':
                broken['contextSha256'] = '0' * 64
            else:
                broken['sections'][0]['entries'][0]['accountIds'] = ['missing']
            draft.write_text(json.dumps(broken), encoding='utf-8')
            with self.assertRaises(ValueError):
                resume_renderer.render(self.source, draft, output, overwrite=True)
            self.assertEqual(output.read_text(), 'Keep this resume')

    def test_resume_escapes_source_and_projection_and_exports_qualifications(self):
        fingerprint = hashlib.sha256(self.source.read_bytes()).hexdigest()
        draft = resume(self.packet, fingerprint)
        attack = '</script><img src=x onerror=alert(1)>'
        draft['sections'][0]['entries'][0]['heading'] = attack
        self.packet['sources'][0]['content'] += attack
        packet = resume_renderer.prepare(self.packet, draft, fingerprint)
        raw = resume_renderer.render_html(packet)
        self.assertNotIn(attack, raw)
        self.assertIn('&lt;/script&gt;', raw)
        plain = resume_renderer.resume_text(packet)
        self.assertIn(self.packet['accounts'][0]['sharedCredit'], plain)
        self.assertIn(self.packet['accounts'][0]['limits'][0], plain)
        self.assertIn('Synthetic demo data', plain)

    def test_images_cannot_escape_input_folder_or_change_without_checksum(self):
        import base64
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aEkwAAAAASUVORK5CYII=')
        (self.folder / 'pixel.png').write_bytes(image)
        base = self.folder / 'selected'
        base.mkdir()
        for path in ['../pixel.png', str(self.folder / 'pixel.png')]:
            with self.assertRaisesRegex(ValueError, 'inside the input folder'):
                renderer.image_data({'file': path}, base)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            renderer.image_data({'_dataUrl': 'data:image/png;base64,' + base64.b64encode(image).decode(), 'sha256': '0' * 64}, base)
        self.packet['accounts'][0]['artifacts'] = [{'id': 'visual', 'title': 'Test image', 'caption': 'Synthetic format fixture', 'file': 'pixel.png'}]
        self.save()
        archive.build(self.source, self.workspace)
        with closing(sqlite3.connect(self.workspace / 'career.sqlite')) as db:
            self.assertEqual(db.execute('SELECT bytes FROM artifacts').fetchone()[0], image)
        (self.folder / 'pixel.png').unlink()
        recovered = self.folder / 'recovered.html'
        archive.export(self.workspace / 'career.sqlite', recovered)
        artifact = renderer.load_packet(recovered)['accounts'][0]['artifacts'][0]
        self.assertEqual(renderer.image_data(artifact, self.folder)[1], image)

    def test_aggregate_size_failure_does_not_replace_sheet(self):
        self.packet['accounts'][0]['summary'] = '<' * 100_000
        self.packet['accounts'] = [dict(copy.deepcopy(self.packet['accounts'][0]), id='account-' + str(i)) for i in range(80)]
        # Escaping expands the repeated field in visible HTML and embedded JSON
        # beyond the 64 MiB document cap while the input remains below 24 MiB.
        for account in self.packet['accounts']:
            account['context'] = 'B' * 100_000
        self.save()
        output = self.folder / 'sheet.html'
        output.write_text('Keep prior sheet', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'HTML sheet exceeds 64 MiB'):
            renderer.render(self.source, output)
        self.assertEqual(output.read_text(), 'Keep prior sheet')


if __name__ == '__main__':
    unittest.main()
