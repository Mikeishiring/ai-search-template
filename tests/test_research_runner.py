import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import fictional_story as fixture
import research_runner as runner
from research_lock import exclusive_run
from research_sheet import events_at, read_json, write_json


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.workspace = fixture.initialize(self.folder)
        self.output = self.folder / 'story.html'

    def run_story(self, worker, **kw):
        return runner.run(self.workspace, self.output, timeout=30, worker=worker, **kw)

    def test_interrupted_worker_resumes_draft_repairs_tail_and_builds_real_sheet(self):
        prepared = []
        charges = []
        def worker(workspace, session, scope, attempt, timeout):
            source = fixture.source(workspace)
            if not prepared:
                prepared.append(fixture.prepare(source))
                charges.append(source.source_calls())
                with (workspace / 'calls.jsonl').open('ab') as stream:
                    stream.write(b'{"sequence":')
                raise subprocess.TimeoutExpired('fictional worker', timeout)
            recovered = source.execute('resume_packet', {})
            self.assertEqual(recovered['draft'], prepared[0][0])
            self.assertEqual(source.source_calls(), charges[0])
            fixture.complete(source, prepared[0])
            return {'exit_code': 0, 'runtime_complete': True, 'unexpected_tools': 0}
        result = self.run_story(worker)
        self.assertEqual(result['worker_attempts'], 2)
        self.assertEqual(result['automatic_retries'], 1)
        self.assertTrue(self.output.exists())
        first = self.workspace / 'research-run/attempt-001'
        self.assertEqual((first / 'interrupted-journal-tail.bin').read_bytes(), b'{"sequence":')
        self.assertEqual(read_json(first / 'receipt.json')['failure'], 'TimeoutExpired')
        before = (self.workspace / 'calls.jsonl').read_bytes()
        rebuilt = self.run_story(lambda *a: self.fail('Sealed run must not call a worker'), force=True)
        self.assertEqual(rebuilt['accounts'], 1)
        self.assertEqual(before, (self.workspace / 'calls.jsonl').read_bytes())

    def test_valid_finish_survives_loss_of_response(self):
        def worker(workspace, *args):
            source = fixture.source(workspace)
            fixture.complete(source, fixture.prepare(source))
            raise ConnectionError('Fictional response lost after durable finish')
        result = self.run_story(worker)
        self.assertEqual(result['worker_attempts'], 1)
        self.assertEqual(result['automatic_retries'], 0)

    def test_revoked_permission_blocks_retry_and_build(self):
        calls = []
        def worker(workspace, *args):
            calls.append(1)
            policy = read_json(workspace / 'policy.json')
            policy['model_processing'] = 'local_only'
            write_json(workspace / 'policy.json', policy)
            return {'exit_code': 1, 'unexpected_tools': 0}
        with self.assertRaisesRegex(ValueError, 'Policy or captures changed'):
            self.run_story(worker)
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.output.exists())

    def test_budget_is_persistent_and_never_fabricates_completion(self):
        calls = []
        def worker(*args):
            calls.append(1)
            return {'exit_code': 1, 'unexpected_tools': 0}
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            self.run_story(worker, max_attempts=2)
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            self.run_story(worker, max_attempts=2)
        self.assertEqual(len(calls), 2)
        self.assertFalse(self.output.exists())

    def test_unexpected_tool_blocks_even_a_saved_finish_and_later_resume(self):
        def worker(workspace, *args):
            source = fixture.source(workspace)
            fixture.complete(source, fixture.prepare(source))
            return {'exit_code': 0, 'unexpected_tools': 1}
        with self.assertRaisesRegex(ValueError, 'Unexpected tools'):
            self.run_story(worker)
        with self.assertRaisesRegex(ValueError, 'Unexpected tools'):
            self.run_story(lambda *a: self.fail('No retry after unexpected tool'))
        self.assertFalse(self.output.exists())

    def test_os_lock_recovers_without_deleting_files_and_excludes_second_owner(self):
        lock = self.workspace / 'lock'
        with exclusive_run(lock):
            with self.assertRaisesRegex(ValueError, 'Another research runner'):
                with exclusive_run(lock):
                    self.fail('Concurrent owner')
        with exclusive_run(lock):
            self.assertTrue(lock.exists())

    def test_lock_is_released_when_owner_process_exits_abruptly(self):
        lock = self.workspace / 'abrupt.lock'
        code = 'import os,sys; from pathlib import Path; from research_lock import exclusive_run; c=exclusive_run(Path(sys.argv[1])); c.__enter__(); print("locked",flush=True); os._exit(9)'
        proc = subprocess.run([sys.executable, '-c', code, str(lock)], capture_output=True, timeout=10)
        self.assertEqual(proc.returncode, 9)
        self.assertIn(b'locked', proc.stdout)
        with exclusive_run(lock):
            pass

    def test_live_worker_probe_does_not_terminate_process(self):
        self.assertTrue(runner.worker_alive(os.getpid()))

    def test_corrupt_middle_and_complete_bad_line_are_never_truncated(self):
        journal = self.workspace / 'calls.jsonl'
        for data in [b'not json\n', b'bad\n{"sequence":2}']:
            journal.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'not a recoverable'):
                runner.recover_journal(self.workspace, self.folder)
            self.assertEqual(journal.read_bytes(), data)

    def test_code_or_scope_change_is_not_silently_resumed(self):
        with self.assertRaisesRegex(ValueError, 'budget exhausted'):
            self.run_story(lambda *a: {'exit_code': 1}, max_attempts=1)
        with patch.object(runner, 'fingerprint', return_value='changed'):
            with self.assertRaisesRegex(ValueError, 'changed'):
                self.run_story(lambda *a: self.fail('Changed scope must not transfer'), max_attempts=1)

    def test_runtime_audit_catches_started_unapproved_tools_before_completion(self):
        path = self.folder / 'stdout.jsonl'
        path.write_text(json.dumps({'type': 'item.started', 'item': {'type': 'command_execution'}}) + '\n', encoding='utf-8')
        self.assertEqual(runner.runtime_audit(path)['unexpected_tools'], 1)

    def test_failure_receipt_does_not_bypass_a_live_worker(self):
        calls = []
        def worker(workspace, session, scope, attempt, timeout):
            calls.append(1)
            write_json(attempt / 'worker.json', {'pid': os.getpid()})
            raise subprocess.TimeoutExpired('Fictional failed termination', timeout)
        with self.assertRaisesRegex(ValueError, 'still be alive'):
            self.run_story(worker)
        self.assertEqual(len(calls), 1)
        self.assertFalse(self.output.exists())

    def test_all_validation_schemas_and_renderer_template_bind_resume(self):
        root = self.folder / 'implementation'
        schema = root / 'ai-search-mvp/model/depth.schema.json'
        template = root / 'skills/career-context-sheet/assets/sheet.html'
        for path in (schema, template):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('original', encoding='utf-8')
        with patch.object(runner, 'ROOT', root):
            before = runner.fingerprint({}, {}, {})
            schema.write_text('changed', encoding='utf-8')
            middle = runner.fingerprint({}, {}, {})
            template.write_text('changed', encoding='utf-8')
            after = runner.fingerprint({}, {}, {})
        self.assertNotEqual(before, middle)
        self.assertNotEqual(middle, after)

    def test_real_worker_timeout_preserves_streamed_diagnostics_and_receipt(self):
        script = self.folder / 'fictional-worker.py'
        script.write_text('import sys,time,json\nsys.stdin.read()\nprint(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"Fictional partial result"}}),flush=True)\nprint("Fictional diagnostic",file=sys.stderr,flush=True)\ntime.sleep(20)\n', encoding='utf-8')
        attempt = self.folder / 'attempt'
        attempt.mkdir()
        _, session, _, scope = runner.load(self.workspace)
        def command(output, schema, **kwargs):
            return [sys.executable, str(script), '--cd', str(attempt), '-']
        with patch.object(runner, 'command', side_effect=command):
            result = runner.launch(self.workspace, session, scope, attempt, 1)
        self.assertTrue(result['timed_out'])
        self.assertTrue(result['runtime_complete'])
        self.assertIn('Fictional partial result', (attempt / 'stdout.jsonl').read_text())
        self.assertIn('Fictional diagnostic', (attempt / 'stderr.txt').read_text())
        self.assertEqual(read_json(attempt / 'receipt.json'), result)
        self.assertFalse(runner.worker_alive(read_json(attempt / 'worker.json')['pid']))

    def test_durable_finish_stops_a_worker_waiting_on_redundant_final_output(self):
        source = fixture.source(self.workspace)
        fixture.complete(source, fixture.prepare(source))
        code = 'import sys,time; sys.stdin.read(); time.sleep(30)'
        proc = subprocess.Popen([sys.executable, '-c', code], stdin=subprocess.PIPE,
                                text=True, start_new_session=os.name != 'nt')
        try:
            with patch.object(runner, 'FINISH_GRACE_SECONDS', 0), patch.object(runner, 'POLL_SECONDS', 0.1):
                receipt = runner.wait_for_worker(proc, {}, self.workspace, 10)
            self.assertTrue(receipt['stopped_after_finish'])
            self.assertFalse(receipt['timed_out'])
            self.assertIsNotNone(proc.poll())
            result = self.run_story(lambda *a: self.fail('A valid sealed journal needs no new worker'))
            self.assertEqual(result['worker_attempts'], 0)
        finally:
            runner.stop_worker(proc)

    def test_finish_marker_ignores_torn_and_nonfinal_receipts(self):
        journal = self.workspace / 'calls.jsonl'
        allowed = json.dumps({'tool': 'finish_check', 'sequence': 1,
                              'result': {'allowed': True, 'receipt_id': 'fictional'}}).encode()
        for raw in (allowed, allowed + b'\n{}\n', allowed + b'\n{"sequence":'):
            journal.write_bytes(raw)
            self.assertIsNone(runner.finish_marker(self.workspace))
        journal.write_bytes(b'x' * 20000 + b'\n' + allowed + b'\n')
        self.assertEqual(runner.finish_marker(self.workspace)[1:], (1, 'fictional'))

    def test_observed_finish_cannot_bypass_the_real_build_gates(self):
        def worker(workspace, *args):
            (workspace / 'calls.jsonl').write_text(json.dumps({'tool': 'finish_check', 'sequence': 1,
                'arguments': {}, 'result': {'allowed': True, 'receipt_id': 'fictional'}}) + '\n', encoding='utf-8')
            return {'exit_code': 1, 'stopped_after_finish': True, 'worker_stopped': True}
        with self.assertRaises(ValueError):
            self.run_story(worker)
        self.assertFalse(self.output.exists())

    def test_actual_mcp_recovers_saved_plan_with_offline_guard_enabled(self):
        source = fixture.source(self.workspace)
        prepared = fixture.prepare(source)
        messages = [{'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                     'params': {'name': 'resume_packet', 'arguments': {}}}]
        proc = subprocess.run([sys.executable, str(runner.ROOT / 'research_sheet_server.py'), str(self.workspace)],
            input=''.join(json.dumps(m) + '\n' for m in messages), text=True,
            capture_output=True, encoding='utf-8', timeout=15)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        reply = json.loads(proc.stdout)
        self.assertFalse(reply['result']['isError'], reply)
        self.assertEqual(json.loads(reply['result']['content'][0]['text'])['draft'], prepared[0])
