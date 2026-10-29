"""Portable-sheet contracts using fictional data and temporary output only."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'career_context', ROOT / 'skills/career-context-sheet/scripts/render_context.py'
)
RENDERER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RENDERER)


class CareerContextTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / 'examples/career-context.json').read_text(encoding='utf-8'))
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)

    def render(self, packet):
        source = self.directory / 'input.json'
        source.write_text(json.dumps(packet), encoding='utf-8')
        destination = self.directory / 'sheet.html'
        RENDERER.render(source, destination)
        return destination

    def test_portable_packet_and_no_change_rebuild(self):
        sheet = self.render(self.packet)
        self.assertEqual(RENDERER.load_packet(sheet), self.packet)
        rebuilt = self.directory / 'rebuilt.html'
        RENDERER.render(sheet, rebuilt)
        self.assertEqual(sheet.read_bytes(), rebuilt.read_bytes())

    def test_source_text_cannot_close_the_json_script_or_add_markup(self):
        hostile = '</script><script>window.injected=true</script><img src=x onerror="alert(1)">'
        self.packet['accounts'][0]['summary'] = hostile
        self.packet['sources'][0]['content'] = hostile
        sheet = self.render(self.packet)
        markup = sheet.read_text(encoding='utf-8')
        self.assertNotIn(hostile, markup)
        self.assertIn('&lt;/script&gt;', markup)
        self.assertEqual(RENDERER.load_packet(sheet), self.packet)

    def test_capabilities_keep_assistance_limits_and_work_links(self):
        sheet = self.render(self.packet)
        markup = sheet.read_text(encoding='utf-8')
        for account in self.packet['accounts']:
            for capability in account.get('capabilities', []):
                self.assertIn(capability['assistance'], markup)
                for limit in capability['limits']:
                    self.assertIn(limit, markup)
                self.assertIn('href="#account-' + account['id'] + '"', markup)
        self.assertEqual(RENDERER.load_packet(sheet), self.packet)
        for account in self.packet['accounts']:
            account.pop('capabilities', None)
        without_skills = self.render(self.packet).read_text(encoding='utf-8')
        self.assertNotIn('id="skills"', without_skills)
        self.assertNotRegex(without_skills, r'<a\b[^>]*\bhref="#skills"')

    def test_capability_validation_and_hostile_text(self):
        capability = self.packet['accounts'][2]['capabilities'][0]
        for field, value in [('kind', 'expert'), ('assistance', ''), ('application', None),
                             ('limits', 'none'), ('limits', ['']), ('name', ' '), ('score', 100)]:
            with self.subTest(field=field, value=value):
                changed = copy.deepcopy(self.packet)
                changed['accounts'][2]['capabilities'][0][field] = value
                with self.assertRaises(ValueError):
                    RENDERER.validate(changed)
        hostile = '</script><script>alert(1)</script>'
        capability['name'] = hostile
        markup = self.render(self.packet).read_text(encoding='utf-8')
        self.assertNotIn(hostile, markup)
        self.assertIn('&lt;/script&gt;', markup)

    def test_presentation_links_cannot_escape_or_execute(self):
        self.packet['presentation'] = {'headline': '<img src=x onerror=alert(1)>', 'files': [{'label': 'Resume', 'path': 'RESUME.html'}]}
        sheet = self.render(self.packet)
        self.assertNotIn('<img src=x onerror=alert(1)>', sheet.read_text(encoding='utf-8'))
        self.assertEqual(RENDERER.load_packet(sheet), self.packet)
        for unsafe in ['../private.txt', 'https://example.invalid/a.html', 'javascript:alert(1)', '/file.txt', 'x%2fsecret.txt', 'x.html?read=private']:
            with self.subTest(path=unsafe):
                self.packet['presentation']['files'][0]['path'] = unsafe
                with self.assertRaisesRegex(ValueError, 'sibling filenames'):
                    self.render(self.packet)

    def test_missing_source_is_rejected(self):
        self.packet['accounts'][0]['sourceRefs'] = ['missing']
        with self.assertRaisesRegex(ValueError, 'references to included sources'):
            self.render(self.packet)

    def test_large_selected_excerpt_collection_round_trips_without_loss(self):
        original = self.packet['sources'][0]
        self.packet['sources'] = [dict(original, id='source-' + str(i), content='Selected excerpt ' + str(i))
                                  for i in range(400)]
        for account in self.packet['accounts']:
            account['sourceRefs'] = [s['id'] for s in self.packet['sources']]
        self.assertEqual(RENDERER.load_packet(self.render(self.packet)), self.packet)

    def test_large_collection_still_has_count_and_aggregate_size_bounds(self):
        original = self.packet['sources'][0]
        self.packet['sources'] = [dict(original, id='source-' + str(i))
                                  for i in range(RENDERER.MAX_SOURCES + 1)]
        with self.assertRaisesRegex(ValueError, 'sources has 2049 entries; maximum is 2048'):
            RENDERER.validate(self.packet)
        self.packet['sources'] = [dict(original, id='source-' + str(i), content='x' * 100_000)
                                  for i in range(260)]
        for account in self.packet['accounts']:
            account['sourceRefs'] = [s['id'] for s in self.packet['sources']]
        with self.assertRaisesRegex(ValueError, 'Sheet exceeds 24 MiB'):
            RENDERER.validate(self.packet)

    def test_large_html_reopens_and_rebuilds_while_output_remains_bounded(self):
        original = self.packet['sources'][0]
        self.packet['sources'] = [dict(original, id='source-' + str(i), content='x' * 70_000)
                                  for i in range(200)]
        for account in self.packet['accounts']:
            account['sourceRefs'] = [s['id'] for s in self.packet['sources']]
        sheet = self.render(self.packet)
        self.assertGreater(sheet.stat().st_size, RENDERER.MAX_PACKET_BYTES)
        self.assertEqual(RENDERER.load_packet(sheet), self.packet)
        rebuilt = self.directory / 'rebuilt.html'
        RENDERER.render(sheet, rebuilt)
        self.assertEqual(sheet.read_bytes(), rebuilt.read_bytes())
        before = sheet.read_bytes()
        with patch.object(RENDERER, 'MAX_DOCUMENT_BYTES', 1000):
            with self.assertRaisesRegex(ValueError, 'HTML sheet exceeds 64 MiB'):
                self.render(self.packet)
            with self.assertRaisesRegex(ValueError, 'HTML sheet exceeds 64 MiB'):
                RENDERER.load_packet(sheet)
        self.assertEqual(sheet.read_bytes(), before)

    def test_unselected_source_dump_is_rejected(self):
        extra = copy.deepcopy(self.packet['sources'][0])
        extra['id'] = 'unselected'
        self.packet['sources'].append(extra)
        with self.assertRaisesRegex(ValueError, 'unreferenced source'):
            self.render(self.packet)

    def test_embedded_image_bytes_do_not_become_canonical_packet_text_on_rebuild(self):
        import base64
        import struct
        import zlib
        # A valid one-pixel PNG with a text chunk exercises the same boundary
        # with a small packet cap instead of allocating dozens of image MiB.
        pixel = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aEkwAAAAASUVORK5CYII=')
        chunk = b'tEXt' + b'Fixture\0' + b'fictional image padding ' * 1000
        image = pixel[:-12] + struct.pack('>I', len(chunk) - 4) + chunk + struct.pack('>I', zlib.crc32(chunk)) + pixel[-12:]
        (self.directory / 'pixel.png').write_bytes(image)
        self.packet['accounts'][0]['artifacts'] = [{'id': 'pixel', 'title': 'Fictional pixel',
            'caption': 'Format test', 'file': 'pixel.png'}]
        cap = len(json.dumps(self.packet).encode()) + 1500
        with patch.object(RENDERER, 'MAX_PACKET_BYTES', cap):
            sheet = self.render(self.packet)
            loaded = RENDERER.load_packet(sheet)
            self.assertGreater(len(json.dumps(loaded).encode()), cap)
            rebuilt = self.directory / 'image-rebuilt.html'
            RENDERER.render(sheet, rebuilt)
            self.assertEqual(sheet.read_bytes(), rebuilt.read_bytes())

    def test_supported_image_bytes_are_preserved_and_path_is_removed(self):
        import base64
        import hashlib
        image = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aEkwAAAAASUVORK5CYII=')
        (self.directory / 'pixel.png').write_bytes(image)
        self.packet['accounts'][0]['artifacts'] = [{
            'id': 'synthetic-pixel', 'title': 'Synthetic pixel',
            'caption': 'Format test only; not work evidence.', 'file': 'pixel.png',
        }]
        sheet = self.render(self.packet)
        artifact = RENDERER.load_packet(sheet)['accounts'][0]['artifacts'][0]
        self.assertNotIn('file', artifact)
        self.assertEqual(artifact['sha256'], hashlib.sha256(image).hexdigest())
        self.assertEqual(RENDERER.image_data(artifact, self.directory), ('image/png', image))
        rebuilt = self.directory / 'rebuilt.html'
        RENDERER.render(sheet, rebuilt)
        self.assertEqual(sheet.read_bytes(), rebuilt.read_bytes())


if __name__ == '__main__':
    unittest.main()
