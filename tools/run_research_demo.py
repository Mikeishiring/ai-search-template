"""One authenticated model run: fictional sources -> checked research -> HTML sheet."""
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research_sheet import (EXPERIMENTS, build, events_at, initialize, load_session,
                            outside_project, write_json)
from model_backend import command, sha
from research_sheet_server import TOOLS


def run(output, workspace=None, resume=False, force=False):
    output = outside_project(output)
    if output.suffix.lower() not in {'.html', '.htm'} or not output.parent.is_dir():
        raise ValueError('Choose an HTML file in an existing folder.')
    if output.exists() and not force:
        raise ValueError('Output exists. Use --force to replace it.')
    workspace = outside_project(workspace or output.parent / ('.' + output.stem + '-research'))
    if resume:
        _, _, _, scope = load_session(workspace)
        events = events_at(workspace)
        if events and events[-1]['tool'] == 'finish_check' and events[-1]['result'].get('allowed'):
            return build(workspace, output, force)
    else:
        initialize(workspace)
        _, _, _, scope = load_session(workspace)
    # Preserve each launch; resuming never changes the scope or discards its journal.
    index = len(list(workspace.glob('attempt-*.receipt.json'))) + 1
    request_file = workspace / f'attempt-{index}.request.json'
    if request_file.exists():
        raise ValueError('An unfinished launch already exists; inspect it before another model call.')
    response = workspace / f'attempt-{index}.response.json'
    prompt = {'synthetic': True, 'scope': scope, 'resuming_saved_research': resume,
              'task': 'Use only synthetic_research to investigate this work and create its checked sheet plan. '
                      'Follow consequential gaps without human prompting. Finish with a valid receipt. '
                      'The host builds the HTML from your saved checked review and plan.'}
    write_json(request_file, prompt)
    cmd = command(response, EXPERIMENTS / 'model/ownership.schema.json')[:-1]
    agent_dir = workspace / 'runtime'
    agent_dir.mkdir(exist_ok=True)
    cmd[cmd.index('--cd') + 1] = str(agent_dir)
    # Reuse the existing ignored CLI state directory from model_backend.command.
    # A new sqlite_home can make the CLI backfill a large local state database per run.
    cmd += ['-c', 'model_instructions_file=' + json.dumps(str(ROOT / 'prompts/RESEARCH-TO-SHEET.md'))]
    config = {'command': sys.executable, 'args': [str(ROOT / 'research_sheet_server.py'), str(workspace)],
              'enabled': True, 'startup_timeout_sec': 60, 'tool_timeout_sec': 30,
              'enabled_tools': [t['name'] for t in TOOLS]}
    for key, value in config.items():
        cmd += ['-c', 'mcp_servers.synthetic_research.' + key + '=' + json.dumps(value)]
    print('Researching the bundled fictional case through your authenticated Codex CLI. '
          'No personal source inputs are accepted.', flush=True)
    started = time.monotonic()
    proc = subprocess.Popen(cmd + ['-'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, encoding='utf-8', errors='replace')
    timed_out = False
    try:
        stdout, stderr = proc.communicate(json.dumps(prompt), timeout=1200)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        timed_out = True
    events = []
    for line in stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    completed = [e['item'] for e in events if e.get('type') == 'item.completed']
    calls = [e for e in completed if e.get('type') not in {'agent_message', 'reasoning'}]
    unexpected = [e for e in calls if e.get('type') != 'mcp_tool_call' or e.get('server') != 'synthetic_research']
    receipt = {'synthetic': True, 'attempt': index, 'resumed': resume, 'exit_code': proc.returncode,
               'timed_out': timed_out, 'elapsed_seconds': round(time.monotonic() - started, 2),
               'provider': 'Authenticated Codex CLI', 'model': 'CLI default; identifier not exposed by this event stream',
               'human_followup_prompts': 0, 'previous_conversation_supplied': False,
               'tool_calls': len(calls), 'unexpected_tools': len(unexpected),
               'prompt_sha256': sha(ROOT / 'prompts/RESEARCH-TO-SHEET.md'),
               'schema_sha256': sha(EXPERIMENTS / 'model/ownership.schema.json'),
               'usage': [e['usage'] for e in events if e.get('usage')]}
    write_json(workspace / f'attempt-{index}.receipt.json', receipt)
    write_json(workspace / f'attempt-{index}.events.json', completed)
    if timed_out or proc.returncode or unexpected or not response.exists():
        # Runtime diagnostics stay in the private workspace; never publish them as fixtures.
        (workspace / f'attempt-{index}.diagnostic.txt').write_text(stderr[-4000:], encoding='utf-8')
        raise ValueError('Model run did not finish cleanly. Its first output and journal are preserved; no automatic retry.')
    result = build(workspace, output, force)
    write_json(workspace / f'attempt-{index}.outcome.json', {'built': True, 'sha256': result['sha256']})
    return result


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    parser.add_argument('--workspace', type=Path)
    parser.add_argument('--resume', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.output, args.workspace, args.resume, args.force)))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
