"""Rebuild the single public document from fictional work, periods and preparation."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('career_context', ROOT / 'skills/career-context-sheet/scripts/render_context.py')
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


def example():
    packet = json.loads((ROOT / 'examples/career-context.json').read_text(encoding='utf-8'))
    quarters = json.loads((ROOT / 'examples/notebook-quarters.json').read_text(encoding='utf-8'))['quarters']
    packet['timeline'] = [{**{k: v for k, v in q.items() if k not in ['style', 'accountId']},
                           'approach': q['style'], 'accountIds': [q['accountId']]} for q in quarters]
    packet['interview'] = json.loads((ROOT / 'examples/interview-preparation.json').read_text(encoding='utf-8'))
    packet['interview']['contextSha256'] = renderer.sections.evidence_fingerprint(packet)
    renderer.validate(packet)
    return packet


if __name__ == '__main__':
    source = ROOT / 'examples/complete-context.json'
    source.write_text(json.dumps(example(), ensure_ascii=True, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(renderer.render(source, ROOT / 'CAREER-CONTEXT.html')))
