"""Real local Git histories test the range boundary without a network service."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from check_git_privacy import check
from check_push_privacy import outgoing_revisions


class PushPrivacyTests(unittest.TestCase):
    public = '1+contributor' + '@' + 'users.noreply.github.com'
    private = 'contributor' + '@' + 'example.invalid'

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-b', 'main', '.')
        self.git('config', 'commit.gpgsign', 'false')
        self.git('config', 'core.hooksPath', str(self.root / 'no-hooks'))

    def git(self, *args):
        return subprocess.check_output(['git', *args], cwd=self.root, stderr=subprocess.PIPE, text=True).strip()

    def commit(self, email):
        self.git('-c', 'user.name=Contributor', '-c', 'user.email=' + email,
                 'commit', '--allow-empty', '-m', 'Fictional change')
        return self.git('rev-parse', 'HEAD')

    def revisions(self, current, previous, ref='main', remote='unused'):
        return outgoing_revisions([f'refs/heads/{ref} {current} refs/heads/{ref} {previous}'], remote, self.root)

    def test_existing_remote_email_does_not_block_clean_new_commit(self):
        old = self.commit(self.private)
        new = self.commit(self.public)
        result = check(self.revisions(new, old), self.root)
        self.assertTrue(result['passed'])
        self.assertEqual(result['commits'], 1)
        self.assertEqual(check(self.revisions(new, new), self.root)['commits'], 0)

    def test_new_private_author_still_blocks(self):
        old = self.commit(self.public)
        new = self.commit(self.private)
        self.assertFalse(check(self.revisions(new, old), self.root)['passed'])

    def test_new_branch_uses_remote_main_not_unpublished_local_main(self):
        old = self.commit(self.private)
        remote = self.root / 'remote.git'
        self.git('init', '--bare', str(remote))
        self.git('push', str(remote), 'HEAD:refs/heads/main')
        good = self.commit(self.public)
        revisions = self.revisions(good, '0' * 40, 'codex/story', str(remote))
        self.assertEqual(check(revisions, self.root)['commits'], 1)
        bad = self.commit(self.private)
        revisions = self.revisions(bad, '0' * 40, 'codex/story', str(remote))
        self.assertFalse(check(revisions, self.root)['passed'])

    def test_new_repository_scans_all_history_and_deletion_scans_none(self):
        old = self.commit(self.private)
        remote = self.root / 'empty.git'
        self.git('init', '--bare', str(remote))
        self.assertFalse(check(self.revisions(old, '0' * 40, remote=str(remote)), self.root)['passed'])
        self.assertEqual(self.revisions('0' * 40, old), [])

    def test_bad_update_and_unavailable_baseline_fail_closed(self):
        new = self.commit(self.public)
        with self.assertRaises(ValueError):
            outgoing_revisions(['invalid'], 'origin', self.root)
        with self.assertRaises(subprocess.CalledProcessError):
            self.revisions(new, '1' * 40)

    def test_hook_uses_actual_push_destination_when_fetch_remote_differs(self):
        old = self.commit(self.public)
        fetched, destination = self.root / 'fetched.git', self.root / 'destination.git'
        for remote in (fetched, destination):
            self.git('init', '--bare', str(remote))
            self.git('push', str(remote), 'HEAD:refs/heads/main')
        bad = self.commit(self.private)
        self.git('push', str(fetched), 'HEAD:refs/heads/main')
        self.git('remote', 'add', 'origin', str(fetched))
        self.git('remote', 'set-url', '--push', 'origin', str(destination))
        script = Path(__file__).resolve().parents[1] / 'tools/check_push_privacy.py'
        result = subprocess.run([sys.executable, str(script), 'origin', str(destination)],
            input=f'refs/heads/codex/story {bad} refs/heads/codex/story {"0" * 40}\n',
            cwd=self.root, text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn('author', result.stderr)
        self.assertNotIn(self.private, result.stderr)
