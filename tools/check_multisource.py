"""Compare bounded discovery strategies on one fixed fictional fixture."""
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'ai-search-mvp'))
from adapter import SyntheticAdapter
from engine import Runner


def compare():
    corpus = json.loads((ROOT / 'ai-search-mvp/fixtures/multisource.corpus.json').read_text())
    scope = json.loads((ROOT / 'ai-search-mvp/fixtures/multisource.scope.json').read_text())
    expected = {r['id'] for r in corpus['records'] if r['source'] in scope['sources'] and r['date'] <= scope['horizon']}
    rows = []
    for name, aliases, followups, enumeration in [
        ('Single-name search only', [], False, False),
        ('Supplied aliases, search only', scope['aliases'], False, False),
        ('Original-window inventory and aliases', scope['aliases'], False, True),
        ('Selected-window and follow-up inventory', scope['aliases'], True, True),
    ]:
        current = copy.deepcopy(corpus)
        for source in current['sources']: source['enumeration'] = enumeration
        adapter = SyntheticAdapter(current)
        runner = Runner(':memory:', adapter, scope | {'aliases': aliases, 'include_followup_roots': followups})
        try: result = runner.run()
        finally: runner.close()
        retained = {r['id'] for r in result['records']}
        rows.append({'strategy': name, 'records': len(retained), 'fixture_records_in_scope': len(expected),
                     'missing_ids': sorted(expected - retained), 'source_calls': len(adapter.calls),
                     'source_locations_with_records': len({r['source'] for r in result['records']}),
                     'outside_scope_reads': sum(c['source'] not in scope['sources'] for c in adapter.calls),
                     'blocked_tasks': sum(t['state'] == 'blocked' for t in result['tasks'])})
    return {'synthetic': True, 'fixture': 'ai-search-mvp/fixtures/multisource.corpus.json',
            'scope': 'ai-search-mvp/fixtures/multisource.scope.json', 'rows': rows,
            'limit': 'Record retrieval in a constructed fixture, including distractors. Not semantic completeness, real connector recall or verified career outcomes.'}


if __name__ == '__main__': print(json.dumps(compare(), indent=2))
