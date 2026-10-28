"""Pre-push email check for outgoing commits, preserving existing remote history."""
import json
from pathlib import Path
import re
import subprocess
import sys

from check_git_privacy import check


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True, stderr=subprocess.PIPE).strip()


def object_id(value):
    return bool(re.fullmatch(r'[0-9a-f]{40}(?:[0-9a-f]{24})?', value))


def outgoing_revisions(lines, remote, root):
    updates = []
    for line in lines:
        fields = line.split()
        if len(fields) != 4 or not all(object_id(fields[i]) for i in (1, 3)):
            raise ValueError('Malformed push update.')
        local_ref, oid, remote_ref, previous = fields
        if set(oid) == {'0'}:  # Deleting a ref publishes no commits.
            continue
        if not remote_ref.startswith('refs/heads/'):
            raise ValueError('This hook checks branches only; tags need separate publication review.')
        updates.append((oid, remote_ref, previous))
    if not updates:
        return []
    if not remote or remote.startswith('-'):
        raise ValueError('Provide the Git remote name or URL.')

    # The destination's advertised main is the published baseline for feature
    # branches. Do not trust stale local tracking refs or exclude local main.
    baseline = None
    if any(ref != 'refs/heads/main' or set(old) == {'0'} for _, ref, old in updates):
        output = git(root, 'ls-remote', '--heads', remote, 'refs/heads/main')
        if output:
            fields = output.split()
            if len(fields) != 2 or not object_id(fields[0]) or fields[1] != 'refs/heads/main':
                raise ValueError('Unexpected remote baseline; fetch and retry.')
            baseline = fields[0]

    tips, published = set(), set()
    for oid, _, old in updates:
        if git(root, 'cat-file', '-t', oid) != 'commit':
            raise ValueError('Branch updates must point directly to commits.')
        tips.add(oid)
        if set(old) != {'0'}:
            published.add(old)
    if baseline:
        published.add(baseline)
    for oid in published:
        if git(root, 'cat-file', '-t', oid) != 'commit':
            raise ValueError('Published baseline is not available locally; fetch and retry.')
    return sorted(tips) + ['^' + oid for oid in sorted(published)]


def main():
    try:
        root = Path(git(Path.cwd(), 'rev-parse', '--show-toplevel'))
        if len(sys.argv) != 3:
            raise ValueError('Pass both pre-push arguments: remote name and destination URL.')
        # A remote's fetch URL can differ from its push URL. Git supplies the
        # actual destination as argv[2]; only that repository is a safe baseline.
        revisions = outgoing_revisions(sys.stdin, sys.argv[2], root)
        if not revisions:
            return 0
        result = check(revisions, root)
        if not result['passed']:
            print(json.dumps(result, indent=2), file=sys.stderr)
            raise ValueError('Use GitHub noreply identities for every outgoing commit and trailer.')
        return 0
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        # Git diagnostics can contain URLs or identities; expose only our own
        # bounded errors, never raw subprocess stderr or command arguments.
        reason = str(error) if isinstance(error, ValueError) else 'Cannot verify outgoing commits; fetch and retry.'
        print('Push blocked: ' + reason, file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
