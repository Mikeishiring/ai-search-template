"""Bounded authenticated research: fictional sources -> checked research -> HTML sheet."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_sheet import initialize, load_session, outside_project


def audit_events(completed):
    diagnostics = [e.get('message', '') for e in completed if e.get('type') == 'error']
    calls = [e for e in completed if e.get('type') not in {'agent_message', 'reasoning', 'error'}]
    unexpected = [e for e in calls if e.get('type') != 'mcp_tool_call' or e.get('server') != 'synthetic_research']
    return calls, unexpected, diagnostics


def run(output, workspace=None, resume=False, force=False, fixture='sheet', max_attempts=3, timeout=3600):
    from research_runner import run as supervised_run
    output = outside_project(output)
    workspace = outside_project(workspace or output.parent / ('.' + output.stem + '-research'))
    if resume:
        load_session(workspace)
    else:
        initialize(workspace, fixture)
    return supervised_run(workspace, output, max_attempts=max_attempts, timeout=timeout, force=force)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--case', choices=['sheet', 'story-depth', 'turning-points'], default='sheet')
    parser.add_argument('--max-attempts', type=int, default=3)
    parser.add_argument('--timeout', type=int, default=3600)
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output, args.workspace, args.resume, args.force, args.case, args.max_attempts, args.timeout)))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
