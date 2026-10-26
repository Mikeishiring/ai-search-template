"""Explicit source policy and local career archive. No network or model calls."""
from datetime import date
import json
from pathlib import Path

import personal
from research_sheet import ROOT, digest, outside_project, read_json, write_json, RENDERER

KINDS = {'channel', 'private_channel', 'dm', 'document', 'repository', 'email', 'calendar'}
CHECKS = ['origins', 'personal_decisions', 'shared_ownership', 'implementation',
          'later_outcomes', 'contrary_evidence', 'personal_meaning', 'story_review']


def validate_policy(policy):
    required = {'subject', 'question', 'earlier_start', 'start', 'end', 'horizon', 'locations', 'import_files',
                'allow_dms', 'allow_private_channels', 'allow_attachments', 'retain_source_text', 'model_processing'}
    if not isinstance(policy, dict) or set(policy) != required:
        raise ValueError('Policy must explicitly specify work, files, locations, DM/private-channel/attachment choices, retention and model processing.')
    for field in ('subject', 'question'):
        if not isinstance(policy[field], str) or not policy[field].strip():
            raise ValueError('Subject and work question are required.')
    for field in ('earlier_start', 'start', 'end', 'horizon'):
        if date.fromisoformat(policy[field]).isoformat() != policy[field]:
            raise ValueError('Use ISO dates: YYYY-MM-DD.')
    if not policy['earlier_start'] <= policy['start'] <= policy['end'] <= policy['horizon']:
        raise ValueError('The follow-up horizon must follow the work window.')
    for field in ('allow_dms', 'allow_private_channels', 'allow_attachments', 'retain_source_text'):
        if type(policy[field]) is not bool:
            raise ValueError(field + ' must be an explicit true/false choice.')
    if policy['model_processing'] not in {'local_only', 'selected_sources'}:
        raise ValueError('Choose local_only or selected_sources for model processing.')
    if not isinstance(policy['locations'], list) or not policy['locations']:
        raise ValueError('Choose at least one exact source location.')
    seen = set()
    for item in policy['locations']:
        if not isinstance(item, dict) or set(item) != {'source', 'container', 'kind'}:
            raise ValueError('Each location needs source, container and kind.')
        if item['source'] not in {'chat', 'docs', 'repo'} or item['kind'] not in KINDS or not isinstance(item['container'], str) or not item['container'].strip():
            raise ValueError('Invalid location. Use a stable channel, folder or repository ID, not a wildcard.')
        if '*' in item['container'] or item['container'] == 'all':
            raise ValueError('Select exact locations; wildcards and all are not allowed.')
        if item['kind'] == 'dm' and not policy['allow_dms']:
            raise ValueError('This selected DM needs explicit DM permission.')
        if item['kind'] == 'private_channel' and not policy['allow_private_channels']:
            raise ValueError('This selected private channel needs explicit permission.')
        key = item['source'], item['container']
        if key in seen:
            raise ValueError('Location IDs must be unique within a source.')
        seen.add(key)
    if not isinstance(policy['import_files'], list) or not policy['import_files'] or any(not isinstance(p, str) or not p for p in policy['import_files']):
        raise ValueError('Select the exact local export files that may be read.')


def initialize(workspace, policy, policy_base=None):
    workspace = outside_project(workspace)
    validate_policy(policy)
    if workspace.exists():
        raise ValueError('Choose a new local folder; existing files are preserved.')
    base = Path(policy_base or Path.cwd())
    policy = dict(policy, import_files=[str((base / p).expanduser().resolve()) for p in policy['import_files']])
    if any(Path(p).is_relative_to(ROOT) for p in policy['import_files']):
        raise ValueError('Keep selected personal exports outside the public checkout.')
    workspace.mkdir(parents=True)
    write_json(workspace / 'policy.json', policy)
    corpus = {'synthetic': False, 'snapshot': date.today().isoformat(),
              'sources': [{'id': s, 'platform': 'Selected local export'} for s in sorted({x['source'] for x in policy['locations']})],
              'records': [], 'attachments': []}
    write_json(workspace / 'corpus.json', corpus)
    write_json(workspace / 'session.json', {'schema': 'career-local/v1', 'policy_hash': digest(policy), 'corpus_hash': digest(corpus)})
    (workspace / '.gitignore').write_text('*\n', encoding='utf-8')
    packet = {'schema': 'career-context/v1', 'updatedAt': corpus['snapshot'], 'reviewStatus': 'draft',
              'person': {'name': policy['subject'], 'overview': '', 'background': []}, 'accounts': [], 'sources': []}
    write_json(workspace / 'context.json', packet)
    RENDERER.render(workspace / 'context.json', workspace / 'CAREER-CONTEXT.html')
    status(workspace)
    return workspace


def load(workspace, *, for_model=False):
    workspace = outside_project(workspace)
    for name in ('session.json', 'policy.json', 'corpus.json', 'calls.jsonl'):
        if (workspace / name).is_symlink():
            raise ValueError('Workspace files must not be symbolic links.')
    session = personal.read_json(workspace / 'session.json')
    policy = personal.read_json(workspace / 'policy.json')
    validate_policy(policy)
    corpus = personal.read_json(workspace / 'corpus.json')
    if session.get('schema') != 'career-local/v1' or session.get('policy_hash') != digest(policy) or session.get('corpus_hash') != digest(corpus):
        raise ValueError('Policy or captures changed outside the configured workflow; research is blocked.')
    if for_model and (policy['model_processing'] != 'selected_sources' or not policy['retain_source_text']):
        raise ValueError('Model access is off. This local-only or metadata-only workspace cannot serve source text to an AI host.')
    for record in corpus['records']:
        if not permitted(policy, record):
            raise ValueError('Stored record is outside the selected policy.')
    scope = {k: policy[k] for k in ('subject', 'question', 'earlier_start', 'start', 'end', 'horizon')}
    scope.update(sources=[s['id'] for s in corpus['sources']], query=policy['question'], timezone='UTC')
    scope['capture_limits'] = corpus.get('capture_limits', [])
    return workspace, session, corpus, scope, policy


def permitted(policy, record):
    if not isinstance(record, dict) or record.get('kind') not in KINDS:
        return False
    location = {'source': record.get('source'), 'container': record.get('container'), 'kind': record['kind']}
    return (location in policy['locations'] and policy['earlier_start'] <= record.get('date', '') <= policy['horizon']
            and (record['kind'] != 'dm' or policy['allow_dms'])
            and (record['kind'] != 'private_channel' or policy['allow_private_channels']))


def import_export(workspace, source_file):
    workspace, session, corpus, _, policy = load(workspace)
    source_file = Path(source_file).expanduser().resolve()
    if str(source_file) not in policy['import_files']:
        raise ValueError('This file was not selected during setup; it will not be read.')
    if (workspace / 'calls.jsonl').exists():
        raise ValueError('Research has started. Keep these captures stable; use a new scoped workspace for changed sources.')
    export = personal.read_json(source_file)
    if not isinstance(export, dict) or set(export) - {'records', 'attachments'} or not isinstance(export.get('records'), list):
        raise ValueError('Use a normalized export object with records and optional attachments.')
    if not isinstance(export.get('attachments', []), list) or any(not isinstance(a, dict) for a in export.get('attachments', [])):
        raise ValueError('Attachments must be a list of normalized attachment objects.')
    allowed = []
    for item in export['records']:
        if not isinstance(item, dict) or item.get('kind') not in KINDS:
            raise ValueError('Every record needs explicit location and privacy kind; unknown kinds are rejected.')
        if not permitted(policy, item):
            continue  # No excluded body or metadata is persisted or served.
        required = {'id', 'source', 'container', 'kind', 'date', 'author', 'title', 'body', 'parent', 'links'}
        if not required <= item.keys() or any(not isinstance(item[k], str) for k in ('id', 'source', 'container', 'date', 'author', 'title', 'body')):
            raise ValueError('Selected records need stable IDs, date, original author, title, body, parent and links.')
        date.fromisoformat(item['date'])
        if not item['id'].startswith(item['source'] + ':') or not isinstance(item['links'], list):
            raise ValueError('Use source-prefixed IDs and explicit links.')
        if item['parent'] is not None and not isinstance(item['parent'], str):
            raise ValueError('Parent must be a record ID or null.')
        if not isinstance(item.get('attachments', []), list) or any(not isinstance(a, str) for a in item.get('attachments', [])):
            raise ValueError('Attachments must be a list of source IDs.')
        if any(not isinstance(link, dict) or set(link) != {'source', 'id'}
               or not all(isinstance(v, str) and v for v in link.values()) for link in item['links']):
            raise ValueError('Each source link must contain source and id strings.')
        row = {k: item[k] for k in required}
        row.update(attachments=item.get('attachments', []) if policy['allow_attachments'] else [],
                   repost_of=item.get('repost_of'), link_only=False)
        if not policy['retain_source_text']:
            row.update(body='', links=[], attachments=[])
        allowed.append(row)
    current = {r['id']: r for r in corpus['records']}
    if len({r['id'] for r in allowed}) != len(allowed):
        raise ValueError('Duplicate IDs in import.')
    available = current | {r['id']: r for r in allowed}
    # Normalize the whole batch before comparison or traversal. Missing parents
    # stay explicit links, including when an identical export is imported again.
    for row in allowed:
        if row['parent'] and (row['parent'] not in available or available[row['parent']]['source'] != row['source']):
            row['links'] = list(row['links']) + [{'source': row['source'], 'id': row['parent']}]
            row['parent'] = None
    for row in allowed:
        if row['id'] in current and current[row['id']] != row:
            raise ValueError('An existing capture differs. Preserve it and start a new scoped capture for the revision.')
        current[row['id']] = row
    for row in current.values():
        seen = set(); node = row
        while node['parent']:
            if node['id'] in seen:
                raise ValueError('Parent cycle in selected records.')
            seen.add(node['id']); node = current[node['parent']]
    attachment_ids = {id for r in current.values() for id in r['attachments']}
    attachments = {a['id']: a for a in corpus['attachments']}
    for a in export.get('attachments', []):
        if policy['retain_source_text'] and policy['allow_attachments'] and a.get('id') in attachment_ids and any(r['source'] == a.get('source') and a['id'] in r['attachments'] for r in current.values()):
            attachments[a['id']] = {k: a[k] for k in ('id', 'source', 'title', 'body', 'unavailable')}
    corpus.update(records=list(current.values()), attachments=list(attachments.values()),
                  capture_limits=['Coverage is limited to selected local exports; source-system completeness is unknown.']
                  + ([] if policy['allow_attachments'] else ['Attachment content was excluded by the workspace policy.'])
                  + ([] if policy['retain_source_text'] else ['Only record metadata was retained; source text is unavailable for research.']))
    if len(json.dumps(corpus).encode()) > personal.MAX_INPUT:
        raise ValueError('Use a smaller scope; local captures are limited to 20 MiB.')
    write_json(workspace / 'corpus.json', corpus)
    session['corpus_hash'] = digest(corpus)
    write_json(workspace / 'session.json', session)
    status(workspace)
    return {'retained_records': len(current), 'selected_in_batch': len(allowed),
            'skipped_records': len(export['records']) - len(allowed), 'network_used': False}


def status(workspace):
    workspace, _, corpus, _, policy = load(workspace)
    from research_sheet import events_at, full_records
    events = events_at(workspace)
    full = full_records(events)
    result = {'local_folder': str(workspace), 'model_processing': policy['model_processing'],
              'source_text_retained': policy['retain_source_text'],
              'locations': [l | {'captured': sum(r['source'] == l['source'] and r['container'] == l['container'] for r in corpus['records']),
                                'read_in_research': sum(r['source'] == l['source'] and r['container'] == l['container'] for r in full.values())} for l in policy['locations']],
              'checklist': {key: 'needs_review' for key in CHECKS},
              'coverage_limit': 'Selected local exports only. Source-system completeness and semantic depth are not established by imported or read counts.',
              'network_used': False}
    if events:
        result['research_queue'] = events[-1]['result'].get('planning', {})
    write_json(workspace / 'checklist.json', result)
    lines = ['# Local career context', '', 'Model processing: ' + policy['model_processing'],
             '', 'Your selected captures, research notes and sheet live in this folder. No source account is connected.',
             '', '| Selected location | Captured | Read in research |', '|---|---:|---:|']
    lines += ['| ' + l['source'] + ' / ' + l['container'].replace('|', '\\|') + ' | ' + str(l['captured']) + ' | ' + str(l['read_in_research']) + ' |' for l in result['locations']]
    lines += ['', result['coverage_limit'], '', '## Depth review', ''] + ['- [ ] ' + key.replace('_', ' ') for key in CHECKS]
    (workspace / 'README.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return result


def wizard(workspace):
    print('Choose what Career Context AI may use. Nothing is connected or uploaded by setup.')
    policy = {k: input(prompt).strip() for k, prompt in [
        ('subject', 'Your name: '), ('question', 'What work should we understand? '),
        ('start', 'Work starts (YYYY-MM-DD): '), ('end', 'Work ends (YYYY-MM-DD): '),
        ('horizon', 'Look for later outcomes through (YYYY-MM-DD): ')]}
    policy['earlier_start'] = input('Look for earlier origins from (YYYY-MM-DD, blank = work start): ').strip() or policy['start']
    def yes(prompt):
        answer = input(prompt + ' [y/N]: ').strip().lower()
        if answer not in {'', 'y', 'yes', 'n', 'no'}:
            raise ValueError('Use y or n; an unclear answer does not grant access.')
        return answer in {'y', 'yes'}
    policy.update(allow_dms=yes('Allow specific DMs you select below?'),
                  allow_private_channels=yes('Allow specific private channels you select below?'),
                  allow_attachments=yes('Include attachment text already present in your selected exports?'),
                  retain_source_text=yes('Keep selected source text in your local context folder?'))
    policy['model_processing'] = 'selected_sources' if yes('Allow an AI host to receive selected source text when you connect this workspace?') else 'local_only'
    policy['locations'] = []
    print('Select exact location IDs. DM permission alone never enables all DMs.')
    while True:
        source = input('Source group: chat, docs (including email/calendar), or repo: ').strip()
        container = input('Exact channel, folder, conversation or repository ID: ').strip()
        kind = input('Kind: channel, private_channel, dm, document, repository, email, calendar: ').strip()
        policy['locations'].append({'source': source, 'container': container, 'kind': kind})
        if not yes('Add another location?'):
            break
    policy['import_files'] = []
    while True:
        policy['import_files'].append(input('Exact local normalized-export JSON path: ').strip())
        if not yes('Select another export file?'):
            break
    return initialize(workspace, policy)
