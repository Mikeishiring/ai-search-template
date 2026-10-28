"""Bounded research supervision. State and diagnostics stay outside the public project."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from research_sheet import (ROOT, EXPERIMENTS, outside_project, read_json, load_session,
                            digest, events_at, build, plan_schema)
from model_backend import command
from research_sheet_server import TOOLS
import depth_protocol as depth
from research_lock import exclusive_run


def save(path, value):
    """Atomically replace a small supervisor checkpoint, including a disk flush."""
    temporary = path.with_suffix(path.suffix + '.writing')
    if path.is_symlink() or temporary.is_symlink():
        raise ValueError('Run state must not be a symbolic link.')
    with temporary.open('w', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)




def load(workspace):
    workspace = outside_project(workspace)
    if read_json(workspace / 'session.json').get('schema') == 'career-local/v1':
        from local_context import load as local_load
        workspace, session, corpus, scope, _ = local_load(workspace, for_model=True)
    else:
        workspace, session, corpus, scope = load_session(workspace)
    return workspace, session, corpus, scope


def fingerprint(session, corpus, scope):
    # Bind resumes to the exact sources, privacy and implementation. No silent upgrades.
    code = {str(p.relative_to(ROOT)): digest(p.read_text(encoding='utf-8'))
            for pattern in ['*.py', 'ai-search-mvp/*.py', 'prompts/RESEARCH-TO-SHEET.md',
                            'ai-search-mvp/model/*.schema.json',
                            'skills/career-context-sheet/scripts/render_context.py',
                            'skills/career-context-sheet/assets/sheet.html']
            for p in ROOT.glob(pattern)}
    return digest([session, corpus, scope, code])


def recover_journal(workspace, attempt):
    """Recover only a torn final append after an interrupted, stopped worker."""
    path = workspace / 'calls.jsonl'
    if not path.exists():
        return
    if path.is_symlink():
        raise ValueError('Journal must not be a symbolic link.')
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    offset = 0
    for index, line in enumerate(lines):
        try:
            event = json.loads(line)
        except (ValueError, UnicodeDecodeError):
            if index != len(lines) - 1 or line.endswith(b'\n') or attempt is None:
                raise ValueError('Journal corruption is not a recoverable final append.') from None
            backup = attempt / 'interrupted-journal-tail.bin'
            if backup.exists():
                raise ValueError('A journal repair already exists; preserve it for inspection.')
            backup.write_bytes(raw[offset:])
            with path.open('r+b') as stream:
                stream.truncate(offset)
                stream.flush()
                os.fsync(stream.fileno())
            return
        if (event.get('sequence') != index + 1 or not isinstance(event.get('arguments'), dict)
                or not isinstance(event.get('result'), dict) or not isinstance(event.get('tool'), str)):
            raise ValueError('Journal sequence or event structure is invalid.')
        offset += len(line)
    if raw and not raw.endswith(b'\n'):
        with path.open('ab') as stream:
            stream.write(b'\n')
            stream.flush()
            os.fsync(stream.fileno())


def runtime_audit(path):
    """Inspect streamed items even when no final response or usage event exists."""
    events, malformed = [], 0
    if path.exists():
        for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
            try:
                events.append(json.loads(line))
            except ValueError:
                malformed += 1
    items = [e['item'] for e in events if isinstance(e.get('item'), dict)]
    unexpected = [i for i in items if i.get('type') not in {'agent_message', 'reasoning', 'error'}
                  and not (i.get('type') == 'mcp_tool_call' and i.get('server') == 'synthetic_research')]
    return {'unexpected_tools': len(unexpected), 'partial_runtime_lines': malformed,
            'usage': [e['usage'] for e in events if e.get('usage')]}


def stop_worker(proc):
    if proc.poll() is not None:
        return
    if os.name == 'nt':
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=30)
    else:
        import signal
        os.killpg(proc.pid, signal.SIGKILL)
    proc.wait(timeout=30)


def worker_alive(pid):
    if os.name == 'nt':
        # os.kill(pid, 0) is not a safe existence probe on Windows.
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x1000, False, pid)
        if not handle:
            return ctypes.get_last_error() != 87  # Unknown/access-denied is fail-closed.
        try:
            code = wintypes.DWORD()
            return not kernel.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value == 259
        finally:
            kernel.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def launch(workspace, session, scope, attempt, timeout):
    """One worker, streamed diagnostics, bounded lifetime. Supervisor owns retries."""
    instructions = (ROOT / 'prompts/RESEARCH-TO-SHEET.md').read_text(encoding='utf-8')
    synthetic = session.get('synthetic') is True
    if not synthetic:
        instructions = instructions.replace('Sources are fictional.', 'Sources are selected local captures, not fictional.')
    (attempt / 'instructions.md').write_text(instructions, encoding='utf-8')
    (attempt / 'schema.json').write_bytes((EXPERIMENTS / 'model/ownership.schema.json').read_bytes())
    definitions = copy.deepcopy(TOOLS)
    next(t for t in definitions if t['name'] == 'sheet_plan')['inputSchema']['properties']['plan'] = plan_schema(session.get('export_protocol'))
    save(attempt / 'tools.json', definitions)
    prompt = {'synthetic': synthetic, 'scope': scope, 'resuming_saved_research': bool(events_at(workspace)),
        'task': 'Inspect research_status and resume_packet first. An empty journal is expected on a new run: '
                'begin discovery within the supplied, already-authorized scope without asking for permission again. '
                'When progress exists, reuse it and continue any unfinished discovery; do not repeat completed work. '
                'Resolve remaining gates, review turning points across selected and reserve material, then finish. '
                'Use only synthetic_research. No other tools, files, memories or source locations. '
                'A stopped worker is not evidence of completion; the saved journal determines progress.'}
    save(attempt / 'request.json', prompt)
    runtime_home = outside_project(Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')))
    cmd = command(attempt / 'response.json', attempt / 'schema.json', runtime_home=runtime_home)[:-1]
    cmd[cmd.index('--cd') + 1] = str(attempt)
    cmd += ['-c', 'model_instructions_file=' + json.dumps(str(attempt / 'instructions.md'))]
    config = {'command': sys.executable, 'args': [str(ROOT / 'research_sheet_server.py'), str(workspace)],
              'enabled': True, 'startup_timeout_sec': 60, 'tool_timeout_sec': 30,
              'enabled_tools': [t['name'] for t in definitions]}
    for key, value in config.items():
        cmd += ['-c', 'mcp_servers.synthetic_research.' + key + '=' + json.dumps(value)]
    started = time.monotonic()
    proc = None
    result = {'exit_code': None, 'timed_out': False, 'runtime_complete': False}
    try:
        with (attempt / 'stdout.jsonl').open('w', encoding='utf-8') as out, (attempt / 'stderr.txt').open('w', encoding='utf-8') as err:
            proc = subprocess.Popen(cmd + ['-'], stdin=subprocess.PIPE, stdout=out, stderr=err,
                text=True, encoding='utf-8', start_new_session=os.name != 'nt')
            save(attempt / 'worker.json', {'pid': proc.pid, 'started_at': time.time()})
            try:
                proc.communicate(json.dumps(prompt), timeout=timeout)
            except subprocess.TimeoutExpired:
                result['timed_out'] = True
                stop_worker(proc)
            result.update(exit_code=proc.returncode, runtime_complete=True)
    finally:
        try:
            if proc is not None:
                stop_worker(proc)
        finally:
            result.update(elapsed_seconds=round(time.monotonic() - started, 2),
                          worker_stopped=proc is None or proc.poll() is not None,
                          **runtime_audit(attempt / 'stdout.jsonl'))
            save(attempt / 'receipt.json', result)
    return result


def run(workspace, output, *, max_attempts=3, timeout=3600, force=False, worker=None):
    if type(max_attempts) is not int or not 1 <= max_attempts <= 5:
        raise ValueError('Choose one to five total worker attempts.')
    if type(timeout) is not int or not 30 <= timeout <= 7200:
        raise ValueError('Choose a worker timeout from 30 to 7200 seconds.')
    output = outside_project(output)
    if output.suffix.lower() not in {'.html', '.htm'} or not output.parent.is_dir():
        raise ValueError('Choose an HTML output in an existing folder outside the public project.')
    if output.exists() and not force:
        raise ValueError('Output exists; use --force to replace it.')
    workspace, session, corpus, scope = load(workspace)
    folder = workspace / 'research-run'
    if folder.is_symlink():
        raise ValueError('Run storage must not be a symbolic link.')
    folder.mkdir(exist_ok=True)
    with exclusive_run(folder / 'running.lock'):
        return run_locked(workspace, output, folder, session, corpus, scope,
                          max_attempts, timeout, force, worker or launch)


def run_locked(workspace, output, folder, session, corpus, scope, maximum, timeout, force, worker):
    expected = fingerprint(session, corpus, scope)
    state_path = folder / 'state.json'
    state = read_json(state_path) if state_path.exists() else {
        'fingerprint': expected, 'max_attempts': maximum, 'timeout': timeout, 'attempts': [], 'status': 'ready'}
    if (state['fingerprint'] != expected or state['max_attempts'] != maximum or state['timeout'] != timeout):
        raise ValueError('Sources, privacy, code or run budget changed; do not silently resume this run.')
    if state['attempts'] != ['attempt-%03d' % (i + 1) for i in range(len(state['attempts']))]:
        raise ValueError('Run attempts must have a contiguous local history.')
    save(state_path, state)
    while True:
        with exclusive_run(workspace / 'research-server.lock'):
            # Reload before every transfer AND before accepting or building saved output.
            _, live, live_corpus, live_scope = load(workspace)
            if fingerprint(live, live_corpus, live_scope) != expected:
                raise ValueError('Research configuration changed; automatic recovery is blocked.')
            attempts = [folder / name for name in state['attempts']]
            for attempt in attempts:
                if attempt.is_symlink():
                    raise ValueError('Attempt storage must not be a symbolic link.')
                attempt.mkdir(exist_ok=True)
                audit = runtime_audit(attempt / 'stdout.jsonl')
                previous = read_json(attempt / 'receipt.json') if (attempt / 'receipt.json').exists() else {}
                if audit['unexpected_tools'] or previous.get('unexpected_tools'):
                    raise ValueError('Unexpected tools detected; no automatic retry or publication.')
                # A failure receipt does not prove termination. A failed taskkill/wait
                # must not allow a second model process to race the first one.
                if (attempt / 'worker.json').exists() and not previous.get('worker_stopped'):
                    pid = read_json(attempt / 'worker.json')['pid']
                    if worker_alive(pid):
                        raise ValueError('An earlier worker may still be alive; recovery will not race it.')
                if not (attempt / 'receipt.json').exists():
                    save(attempt / 'receipt.json', {'exit_code': None, 'runtime_complete': False,
                        'failure': 'supervisor_interrupted', **audit})
            recover_journal(workspace, attempts[-1] if attempts else None)
            events = events_at(workspace)
            if events and events[-1]['tool'] == 'finish_check' and events[-1]['result'].get('allowed'):
                result = build(workspace, output, force)
                state.update(status='complete', output_sha256=result['sha256'])
                save(state_path, state)
                return result | {'worker_attempts': len(attempts), 'automatic_retries': max(0, len(attempts) - 1)}
            if len(attempts) >= maximum or len(events) >= depth.REQUEST_LIMIT:
                state['status'] = 'budget_exhausted'
                save(state_path, state)
                raise ValueError('Research budget exhausted. Saved progress is incomplete; no finished sheet was produced.')
            name = 'attempt-%03d' % (len(attempts) + 1)
            attempt = folder / name
            state['attempts'].append(name)
            state['status'] = 'running'
            save(state_path, state)
            attempt.mkdir()
        print(f'Research worker {len(state["attempts"])}/{maximum}; continuing saved progress.', flush=True)
        try:
            receipt = worker(workspace, session, scope, attempt, timeout)
        except (OSError, subprocess.SubprocessError) as error:
            receipt = (read_json(attempt / 'receipt.json') if (attempt / 'receipt.json').exists()
                       else {'exit_code': None, 'runtime_complete': False})
            receipt.update(failure=type(error).__name__, **runtime_audit(attempt / 'stdout.jsonl'))
        save(attempt / 'receipt.json', receipt)
        if receipt.get('unexpected_tools'):
            state['status'] = 'unexpected_tools'
            save(state_path, state)
            raise ValueError('Unexpected tools detected; automatic recovery is blocked.')
        state['status'] = 'checking_progress'
        save(state_path, state)
