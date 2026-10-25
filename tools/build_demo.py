"""Rebuild the public example from the fixed, fictional packet only."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('career_context_cli', ROOT / 'career_context.py')
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)
source = ROOT / 'examples/career-context.json'
if json.loads(source.read_text(encoding='utf-8')).get('synthetic') is not True:
    raise SystemExit('Public example must explicitly contain synthetic data.')
result = cli.renderer().render(source, ROOT / 'CAREER-CONTEXT.html')
print(json.dumps({key: result[key] for key in ('accounts', 'sources', 'bytes', 'sha256')}))
