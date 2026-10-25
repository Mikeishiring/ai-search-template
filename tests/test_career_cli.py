"""First-use and private-output boundaries for the friendly command."""
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import career_context


class CareerCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.output = self.directory / 'context.html'

    def run_cli(self, *args):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            career_context.main([str(a) for a in args])

    def test_demo_is_offline_and_preserves_existing_output(self):
        with patch('socket.socket', side_effect=AssertionError('Network forbidden')):
            self.run_cli('demo', self.output)
        packet = career_context.renderer().load_packet(self.output)
        self.assertTrue(packet['synthetic'])
        self.assertEqual(len(packet['accounts']), 3)
        self.output.write_text('Keep my work', encoding='utf-8')
        with self.assertRaises(SystemExit): self.run_cli('demo', self.output)
        self.assertEqual(self.output.read_text(), 'Keep my work')
        self.run_cli('demo', self.output, '--force')
        self.assertIn('Synthetic demo data', self.output.read_text(encoding='utf-8'))

    def test_public_checkout_rejects_personal_inputs_and_outputs(self):
        with self.assertRaises(SystemExit): self.run_cli('demo', ROOT / 'forbidden.html')
        with self.assertRaises(SystemExit):
            self.run_cli('render', ROOT / 'examples/career-context.json', self.output)
        self.assertFalse(self.output.exists())

    def test_render_existing_sheet_retains_packet_and_draft_state(self):
        self.run_cli('demo', self.output)
        rebuilt = self.directory / 'rebuilt.html'
        self.run_cli('render', self.output, rebuilt)
        self.assertEqual(self.output.read_bytes(), rebuilt.read_bytes())

    def test_failed_packet_does_not_replace_output(self):
        source = self.directory / 'input.json'
        source.write_text('{"schema":"wrong"}', encoding='utf-8')
        self.output.write_text('Keep my work', encoding='utf-8')
        with self.assertRaises(SystemExit): self.run_cli('render', source, self.output, '--force')
        self.assertEqual(self.output.read_text(), 'Keep my work')

    def test_synthetic_flag_is_optional_and_strict(self):
        packet = json.loads((ROOT / 'examples/career-context.json').read_text(encoding='utf-8'))
        for flag in (None, False):
            value = copy.deepcopy(packet)
            if flag is None: value.pop('synthetic')
            else: value['synthetic'] = flag
            source = self.directory / 'input.json'
            source.write_text(json.dumps(value), encoding='utf-8')
            self.run_cli('render', source, self.output, '--force')
            markup = self.output.read_text(encoding='utf-8')
            self.assertNotIn('<p class="demo-notice">', markup)
        packet['synthetic'] = 'false'
        with self.assertRaises(ValueError): career_context.renderer().validate(packet)

    def test_missing_fields_have_friendly_error(self):
        source = self.directory / 'input.json'
        source.write_text('{"schema":"career-context/v1","reviewStatus":"draft"}', encoding='utf-8')
        error = io.StringIO()
        with contextlib.redirect_stderr(error), self.assertRaises(SystemExit):
            career_context.main(['render', str(source), str(self.output)])
        self.assertIn('Could not create the sheet', error.getvalue())
        self.assertNotIn('Traceback', error.getvalue())


if __name__ == '__main__': unittest.main()
