"""Retrieval mechanics only: these tests do not grade a model's fit judgments."""
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/career-context-sheet/scripts/retrieve_context.py'
spec = importlib.util.spec_from_file_location('retrieval_test_module', SCRIPT)
retrieval = importlib.util.module_from_spec(spec)
spec.loader.exec_module(retrieval)


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / 'examples/complete-context.json').read_text(encoding='utf-8'))
        self.source = self.packet['sources'][0]
        self.source['content'] = 'Proposal: try a Referral Leaderboard. Later review: tracking remains manual.'
        self.period = self.packet['timeline'][0]
        self.period['sourceRefs'] = [self.source['id']]
        self.period['focus'] = 'Referral programme planning.'
        for account in self.packet['accounts']:
            if self.source['id'] in account['sourceRefs']:
                account['sourceRefs'].remove(self.source['id'])
        # search() can inspect a partial in-memory fixture; the CLI validates a full packet.

    def test_finds_source_absent_from_work_index_and_retains_direct_links(self):
        result = retrieval.search(self.packet, ['leaderboard'])['layers']
        self.assertEqual(result['accounts']['totalMatches'], 0)
        hit = result['sources']['hits'][0]
        self.assertEqual(hit['id'], self.source['id'])
        self.assertEqual(hit['links']['accountIds'], [])
        self.assertIn(self.period['id'], hit['links']['timelineIds'])
        self.assertIn('Proposal:', hit['matches'][0]['snippet'])
        self.assertIn('tracking remains manual', hit['matches'][0]['snippet'])

    def test_case_insensitive_literals_preserve_original_and_search_limits(self):
        account = self.packet['accounts'][0]
        account['limits'] = ['Independent C++ fluency is not claimed.']
        results = retrieval.search(self.packet, ['c++'])['layers']['accounts']['hits']
        self.assertEqual(results[0]['matches'][0]['field'], 'limits[0]')
        self.assertIn('C++', results[0]['matches'][0]['snippet'])
        self.assertEqual(retrieval.search(self.packet, ['.*'])['layers']['sources']['totalMatches'], 0)

    def test_pagination_exposes_remaining_sources_without_deduplicating_claims(self):
        for index in range(5):
            self.packet['sources'].append(dict(self.source, id=f'copy-{index}'))
        first = retrieval.search(self.packet, ['leaderboard'], layers=['sources'], limit=2)['layers']['sources']
        second = retrieval.search(self.packet, ['leaderboard'], layers=['sources'], limit=2,
                                  offset=first['nextOffset'])['layers']['sources']
        self.assertEqual(first['totalMatches'], 6)
        self.assertEqual(second['offset'], 2)
        self.assertFalse({h['id'] for h in first['hits']} & {h['id'] for h in second['hits']})
        self.assertIsNone(retrieval.search(self.packet, ['leaderboard'], layers=['sources'],
                                         limit=2, offset=4)['layers']['sources']['nextOffset'])

    def test_no_match_is_empty_retrieval_and_full_record_is_unchanged(self):
        before = copy.deepcopy(self.packet)
        result = retrieval.search(self.packet, ['neverseenword'])
        self.assertTrue(all(layer['totalMatches'] == 0 for layer in result['layers'].values()))
        read = retrieval.read_record(self.packet, 'sources:' + self.source['id'])
        self.assertEqual(read['record'], self.source)
        self.assertEqual(before, self.packet)

    def test_transport_and_source_locators_do_not_create_capability_hits(self):
        self.source['locator'] = 'https://example.invalid/locator-sentinel'
        self.packet['accounts'][0]['artifacts'] = [{'file': 'transport-sentinel.png', '_dataUrl': 'transport-sentinel'}]
        for query in ['locator-sentinel', 'transport-sentinel']:
            self.assertTrue(all(r['totalMatches'] == 0 for r in retrieval.search(self.packet, [query])['layers'].values()))
        self.assertNotIn('artifacts', retrieval.read_record(self.packet, 'accounts:' + self.packet['accounts'][0]['id'])['record'])

    def test_invalid_bounds_and_record_fail_clearly(self):
        for options in [{'queries': ['']}, {'queries': ['x'], 'limit': 0},
                        {'queries': ['x'], 'offset': -1}, {'queries': ['x'], 'layers': ['bad']}]:
            with self.assertRaises(ValueError):
                retrieval.search(self.packet, **options)
        for key in ['bad', 'sources:missing']:
            with self.assertRaises(ValueError):
                retrieval.read_record(self.packet, key)

    def test_portable_bundle_reads_json_and_html_without_modifying_either(self):
        sys.path.insert(0, str(ROOT))
        from tools.build_skill import build
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            build(folder / 'skill.zip')
            with zipfile.ZipFile(folder / 'skill.zip') as archive:
                archive.extractall(folder)
            script = folder / 'career-context-sheet/scripts/retrieve_context.py'
            for source in [ROOT / 'examples/complete-context.json', ROOT / 'CAREER-CONTEXT.html']:
                before = source.read_bytes()
                result = subprocess.run([sys.executable, '-I', str(script), str(source), '--query', 'the', '--limit', '2'],
                                        cwd=folder, text=True, capture_output=True, timeout=20)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(set(json.loads(result.stdout)['layers']), set(retrieval.LAYERS))
                self.assertEqual(source.read_bytes(), before)
            invalid = folder / 'invalid.json'
            invalid.write_text('{"schema":"bad"}')
            result = subprocess.run([sys.executable, '-I', str(script), str(invalid), '--query', 'x'],
                                    cwd=folder, text=True, capture_output=True, timeout=20)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main()
