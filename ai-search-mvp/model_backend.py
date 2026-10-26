"""Authenticated Codex CLI reviewer. Only a validated synthetic packet crosses the model boundary."""
from __future__ import annotations
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def executable():
    # Prefer the active CLI installation; retain the earlier npm layout fallback.
    active = shutil.which('codex')
    if active:
        return Path(active)
    base = Path(os.environ.get('APPDATA', '')) / 'npm/node_modules/@openai/codex'
    matches = list(base.glob('node_modules/@openai/codex-*/vendor/*/bin/codex.exe'))
    if len(matches) != 1:
        raise RuntimeError('Install Codex and put its executable on PATH before running a model trial')
    return matches[0]


def command(output, schema):
    workspace = ROOT / 'runs/model-workspace'
    workspace.mkdir(parents=True, exist_ok=True)
    cmd = [str(executable()), 'exec', '--ignore-user-config', '--ephemeral', '--skip-git-repo-check',
           '--sandbox', 'read-only', '--color', 'never', '--json', '--cd', str(workspace),
           '--output-last-message', str(output), '--output-schema', str(schema)]
    config = {
        'project_doc_max_bytes': 0,
        'model_instructions_file': str(ROOT / 'model/reviewer-prompt.txt'),
        'web_search': 'disabled',
        'skills.max_context_tokens': 1,
        'sqlite_home': str(ROOT / 'runs/model-workspace'),
        'approval_policy': 'never',
    }
    for feature in ['shell_tool','shell_snapshot','apps','plugins','hooks','memories','multi_agent',
                    'multi_agent_v2','browser_use','browser_use_external','computer_use','in_app_browser',
                    'image_generation','goals','tool_suggest','workspace_dependencies']:
        config['features.' + feature] = False
    for key, value in config.items():
        cmd += ['-c', key+'='+json.dumps(value)]
    # Disable skill discovery entries without reading their contents.
    skill_overrides = []
    for folder in [Path.home()/'.codex/skills', Path.home()/'.agents/skills']:
        if folder.exists():
            for file in folder.glob('**/SKILL.md'):
                skill_overrides.append('{path='+json.dumps(str(file.parent))+',enabled=false}')
    if skill_overrides:
        cmd += ['-c', 'skills.config=['+','.join(skill_overrides)+']']
    return cmd + ['-']


def validate_packet(packet):
    if packet.get('synthetic') is not True or set(packet) - {'synthetic','question','scope','records','retrieval_limits'}:
        raise ValueError('Only the synthetic review packet schema is accepted')
    if not packet.get('records') and packet.get('question') != 'Connection smoke test':
        raise ValueError('No retained evidence')
    for r in packet.get('records', []):
        if set(r) - {'id','source','date','author','body','parent','links','title','attachments','link_only','repost_of'}:
            raise ValueError('Unexpected record field')
    text = json.dumps(packet)
    if re.search(r'(?i)C:[/\\]|/Users/|xox[baprs]-|sk-ant-|slack\.com/archives', text):
        raise ValueError('Packet contains a path, credential pattern or live source locator')


def invoke(packet, folder, timeout=240):
    validate_packet(packet)
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / 'review.json'
    if output.exists():
        raise ValueError('A model output already exists; do not silently replace the first attempt')
    serialized = json.dumps(packet, ensure_ascii=False, indent=2)
    (folder / 'packet.json').write_text(serialized, encoding='utf-8')
    cmd = command(output, ROOT / 'model/review.schema.json')
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input=serialized, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
    except subprocess.TimeoutExpired as error:
        (folder/'transport-failure.json').write_text(json.dumps({'kind':'timeout','seconds':timeout,'model_output_received':output.exists()}),encoding='utf-8')
        diagnostic=error.stderr or b''
        if isinstance(diagnostic,bytes): diagnostic=diagnostic.decode('utf-8','replace')
        print(json.dumps({'model_call':'timeout','diagnostic':diagnostic[-1800:]}))
        raise RuntimeError('Reviewer transport timed out') from None
    events = []
    for line in proc.stdout.splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            pass
    calls = [e for e in events if e.get('item', {}).get('type') not in {None,'agent_message','reasoning'}]
    receipt = {'provider':'Authenticated Codex CLI', 'model_selection':'CLI default; no model override',
               'exit_code':proc.returncode,'elapsed_seconds':round(time.monotonic()-started,2),
               'packet_sha256':hashlib.sha256(serialized.encode()).hexdigest(),
               'prompt_sha256':sha(ROOT/'model/reviewer-prompt.txt'),
               'schema_sha256':sha(ROOT/'model/review.schema.json'),
               'tool_events':len(calls), 'ephemeral':True,'user_config_loaded':False,
               'usage':[e.get('usage') for e in events if e.get('usage')],
               'event_types':[e.get('type') for e in events]}
    (folder/'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
    # Store model messages only; discard stderr paths and unrelated runtime diagnostics.
    (folder/'messages.json').write_text(json.dumps([e['item'] for e in events if e.get('item',{}).get('type')=='agent_message'],indent=2),encoding='utf-8')
    if proc.returncode or not output.exists():
        print(json.dumps({'model_call':'failed','exit_code':proc.returncode,'diagnostic':proc.stderr[-1600:]}))
        raise RuntimeError('Model call did not produce a response')
    if calls:
        raise RuntimeError('Unexpected tool events: output excluded from the evaluation')
    return json.loads(output.read_text(encoding='utf-8')), receipt


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['smoke','review'])
    args=parser.parse_args()
    if args.action=='smoke':
        packet={'synthetic':True,'question':'Connection smoke test','scope':{},'records':[],
                'retrieval_limits':['Return account READY, empty claims and rejected_conclusions; unknowns may state there is no evidence.']}
        result,receipt=invoke(packet,ROOT/'runs/model-smoke',timeout=60)
    else:
        # The sole permitted review fixture is fixed; no arbitrary input path.
        result_path=ROOT/'runs/semantic/result.json'
        result_data=json.loads(result_path.read_text(encoding='utf-8'))
        packet={'synthetic':True,'question':result_data['scope']['question'],'scope':result_data['scope'],
                'records':result_data['records'], 'retrieval_limits':result_data['coverage']}
        result,receipt=invoke(packet,ROOT/'runs/semantic/model')
    print(json.dumps({'model_call':'complete','claims':len(result['claims']),'elapsed_seconds':receipt['elapsed_seconds'],'tool_events':receipt['tool_events']}))
