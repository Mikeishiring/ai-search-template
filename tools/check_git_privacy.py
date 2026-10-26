"""Screen public commit identities without printing rejected contact details.

Run before publishing a commit range. File-content checks remain separate.
GitHub-created merges require the account's private-email setting as well.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
EMAIL = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b')


def public_email(value):
    local, separator, domain = value.casefold().rpartition('@')
    return bool(separator and local and (domain == 'users.noreply.github.com'
                or (domain == 'github.com' and local == 'noreply')))


def inspect_commit(oid, raw):
    headers, _, message = raw.partition('\n\n')
    errors = []
    for field in ['author', 'committer']:
        line = next((l for l in headers.splitlines() if l.startswith(field + ' ')), '')
        match = re.search(r'<([^<>]*)> \d+ [+-]\d{4}$', line)
        if not match or not public_email(match[1]):
            errors.append({'commit': oid, 'field': field, 'reason': 'Use an explicitly public GitHub noreply identity.'})
    for email in EMAIL.findall(message):
        if not public_email(email):
            errors.append({'commit': oid, 'field': 'message_or_trailer', 'reason': 'Non-public contact address in commit message.'})
            break
    return errors


def check(revisions, root=ROOT):
    if not revisions or any(r.startswith('-') for r in revisions):
        raise ValueError('Provide commit refs or ranges, not Git options.')
    commits = subprocess.check_output(['git', 'rev-list', *revisions, '--'], cwd=root, text=True).splitlines()
    errors = []
    for oid in commits:
        raw = subprocess.check_output(['git', 'cat-file', 'commit', oid], cwd=root).decode('utf-8', errors='replace')
        errors += inspect_commit(oid, raw)
    return {'commits': len(commits), 'passed': not errors, 'findings': errors,
            'scope': 'Author, committer and message/trailer email addresses in the selected commit range; no remote writes.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('revisions', nargs='+', help='For example origin/main..HEAD, or HEAD for all reachable history')
    args = parser.parse_args()
    result = check(args.revisions)
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)
