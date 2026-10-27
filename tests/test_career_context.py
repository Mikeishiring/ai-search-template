"""Portable-sheet contracts using fictional data and temporary output only."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest


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

    def test_unselected_source_dump_is_rejected(self):
        extra = copy.deepcopy(self.packet['sources'][0])
        extra['id'] = 'unselected'
        self.packet['sources'].append(extra)
        with self.assertRaisesRegex(ValueError, 'unreferenced source'):
            self.render(self.packet)

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
