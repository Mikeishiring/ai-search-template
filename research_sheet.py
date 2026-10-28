"""Compile a checked research journal into the portable career-context format."""
import copy
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
EXPERIMENTS = ROOT / 'ai-search-mvp'
sys.path.insert(0, str(EXPERIMENTS))
from completion_server import spans
from mcp_server import check
from ownership_review import compile_review, draft_hash, evidence_version
from career_context import renderer
import depth_protocol as depth
import narrative_retention as retention
import turning_points
RENDERER = renderer()

FIELDS = ('summary', 'context', 'aim', 'contribution', 'decisions', 'sharedCredit', 'outcome')
IDS = {'type': 'array', 'items': {'type': 'string'}}
PLAN_SCHEMA = {
    'type': 'object', 'additionalProperties': False,
    'required': ['overview', 'accounts'],
    'properties': {
        'overview': IDS,
        'accounts': {'type': 'array', 'minItems': 1, 'maxItems': 12, 'items': {
            'type': 'object', 'additionalProperties': False,
            'required': ['id', 'title', 'period', *FIELDS, 'questions'],
            'properties': {
                **{key: {'type': 'string'} for key in ('id', 'title', 'period')},
                **{key: IDS for key in FIELDS},
                'questions': {'type': 'array', 'items': {'type': 'string'}},
            },
        }},
    },
}

EXPORT_PROTOCOL = 'career-sheet/v2'
CURRENT_PLAN_SCHEMA = copy.deepcopy(PLAN_SCHEMA)
CURRENT_PLAN_SCHEMA['required'].append('schema')
CURRENT_PLAN_SCHEMA['properties']['schema'] = {'type': 'string', 'enum': [EXPORT_PROTOCOL]}
_current_account = CURRENT_PLAN_SCHEMA['properties']['accounts']['items']
_current_account['required'].append('limits')
_current_account['properties']['limits'] = IDS


def plan_schema(protocol):
    if protocol is None:
        return PLAN_SCHEMA
    if protocol != EXPORT_PROTOCOL:
        raise ValueError('Unsupported sheet export protocol.')
    return CURRENT_PLAN_SCHEMA



def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, value):
    Path(path).write_bytes((json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode('utf-8'))


def outside_project(path):
    path = Path(path).expanduser().resolve()
    if path.is_relative_to(ROOT):
        raise ValueError('Keep the research workspace and output outside the public project.')
    return path


FIXTURES = {'sheet', 'story-depth', 'turning-points'}


def initialize(workspace, fixture='sheet'):
    """Only the bundled fictional case can enter the automated model path."""
    workspace = outside_project(workspace)
    if workspace.exists():
        raise ValueError('Research workspace already exists. Resume it or choose a new empty location.')
    if fixture not in FIXTURES:
        raise ValueError('Choose a bundled fictional research case.')
    corpus = read_json(EXPERIMENTS / ('fixtures/' + fixture + '.corpus.json'))
    scope = read_json(EXPERIMENTS / ('fixtures/' + fixture + '.scope.json'))
    workspace.mkdir(parents=True)
    write_json(workspace / 'session.json', {
        'schema': 'career-research/v1', 'synthetic': True,
        'corpus_hash': digest(corpus), 'scope_hash': digest(scope),
        'scope': scope, 'source_fixture': fixture,
        'depth_protocol': depth.PROTOCOL,
        'retention_protocol': retention.PROTOCOL,
        'turning_point_protocol': turning_points.PROTOCOL,
        'export_protocol': EXPORT_PROTOCOL,
    })
    return workspace


def load_session(workspace):
    workspace = outside_project(workspace)
    session = read_json(workspace / 'session.json')
    fixture = session.get('source_fixture')
    if fixture not in FIXTURES:
        raise ValueError('Session does not match a bundled fictional case.')
    corpus = read_json(EXPERIMENTS / ('fixtures/' + fixture + '.corpus.json'))
    scope = read_json(EXPERIMENTS / ('fixtures/' + fixture + '.scope.json'))
    if (session.get('schema') != 'career-research/v1' or session.get('synthetic') is not True
            or session.get('scope') != scope
            or session.get('corpus_hash') != digest(corpus) or session.get('scope_hash') != digest(scope)):
        raise ValueError('Session does not match the fixed fictional case. No model call is allowed.')
    return workspace, session, corpus, scope


def events_at(workspace):
    path = Path(workspace) / 'calls.jsonl'
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def full_records(events):
    return {r['id']: r for e in events if e['result'].get('full_records')
            for r in e['result'].get('items', []) if 'parent' in r}


def compile_sheet(raw, plan, records, events, scope, snapshot, *, draft=False, synthetic=True):
    """No model rewrite: fields select checked claims and original source spans."""
    protocol = plan.get('schema')
    check(plan, plan_schema(protocol))
    fields = FIELDS + ('limits',) if protocol else FIELDS
    review, validation = compile_review(raw, records, events, draft=draft)
    errors = list(validation['errors'])
    claims = {c['id']: c for c in review['claims']}
    if not claims:
        errors.append('A sheet needs at least one supported claim.')
    if len(claims) != len(review['claims']):
        errors.append('Claim IDs must be unique.')
    claimed = set()
    account_ids = set()
    account_claims = []
    for account in plan['accounts']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', account['id']) or account['id'] in account_ids:
            errors.append('Accounts need unique safe IDs.')
        account_ids.add(account['id'])
        selected = []
        detail_claims = set()
        detail_texts = set()
        for field in fields:
            ids = account[field]
            if len(ids) != len(set(ids)) or any(i not in claims for i in ids):
                errors.append('Unknown or duplicate claim in ' + account['id'] + '.' + field)
            if protocol and field != 'summary':
                for cid in ids:
                    if cid not in claims:
                        continue
                    wording = ' '.join(claims[cid]['statement'].split()).casefold()
                    if cid in detail_claims or wording in detail_texts:
                        errors.append(account['id'] + ': give each detail claim one field; split repeated compound prose into supported field-specific claims.')
                    detail_claims.add(cid)
                    detail_texts.add(wording)
            selected.extend(ids)
        if protocol:
            questions = [' '.join(q.split()).casefold() for q in account['questions']]
            if any(not q for q in questions) or len(questions) != len(set(questions)):
                errors.append(account['id'] + ': keep each person-facing question once.')
        if not selected:
            errors.append('Each account needs supported content.')
        claimed.update(selected)
        account_claims.append(set(selected))
    if claimed != set(claims):
        errors.append('Every checked claim must survive in an account field.')
    if protocol and len(plan['overview']) != len(set(plan['overview'])):
        errors.append('Overview must not repeat a claim.')
    if not plan['overview'] or any(i not in claimed for i in plan['overview']):
        errors.append('Overview must select claims represented in the accounts.')
    if errors:
        return None, validation | {'valid': False, 'errors': errors}

    known = {r['id']: r for r in records}
    catalog = {(r['id'], s['span_id']): s for r in records for s in spans(r)}
    selected_spans = {}
    for claim in raw['claims']:
        for evidence in claim['evidence']:
            pair = evidence['record_id'], evidence['span_id']
            selected_spans[pair] = catalog[pair]
    source_ids = {pair: 'evidence-' + digest(pair)[:20] for pair in selected_spans}
    sources = []
    for pair, span in selected_spans.items():
        record = known[pair[0]]
        sources.append({
            'id': source_ids[pair], 'label': record['title'] + ' (' + record['author'] + ')',
            'kind': 'source_excerpt', 'date': record['date'], 'content': span['quote'],
            'scope': ('Fictional original excerpt. Record ' if synthetic else 'Selected original excerpt. Record ') + pair[0] + '; span ' + pair[1]
                     + '. Source report, not independent verification.',
        })

    def sentence(id):
        claim = claims[id]
        return (claim['statement'] + ' ' + claim['limits']).strip()

    accounts = []
    raw_claims = {c['id']: c for c in raw['claims']}
    stop = next((e['result'] for e in reversed(events) if e['tool'] == 'finish_check'
                 and e['result'].get('receipt_id') == raw.get('stop_receipt_id')), None)
    universal_limits = [('AI-authored draft from fictional sources; ' if synthetic else 'AI-authored draft; ') + 'the person has not reviewed it.']
    universal_limits += raw['unknowns']
    universal_limits += scope.get('capture_limits', [])
    unavailable = [e for e in events if e['tool'] in {'read_record', 'read_attachment', 'read_context'}
                   and (e['result'].get('error') or e['result'].get('unavailable'))]
    universal_limits += ['Source unavailable or excluded: ' + e['arguments'].get('id', 'unknown record') + '.' for e in unavailable]
    universal_limits += ['Rejected interpretation: ' + r['statement'] + ' ' + r['reason'] for r in raw['rejected_conclusions']]
    universal_limits += ['Evidence coverage: ' + n['reason'] for n in raw['coverage_notes']]
    if stop and any(stop.get('unresolved', {}).values()):
        universal_limits.append('Research stopped with unresolved work: ' + stop['status'] + '. See the saved continuation queue.')
    if stop:
        planning = stop.get('planning', {})
        if planning.get('outside_scope_links') or planning.get('unavailable_or_excluded_links'):
            universal_limits.append('Some source links were outside the selected scope or unavailable in the local exports; those linked originals were not read.')
    audit = depth.current_review(events, evidence_version(records, events))
    if audit and (audit['result']['draft_hash'] != draft_hash(raw) or audit['result']['plan_hash'] != digest(plan)):
        audit = None
    for account, selected in zip(plan['accounts'], account_claims):
        item = {k: account[k] for k in ('id', 'title', 'period')}
        for field in FIELDS:
            texts = [sentence(i) for i in account[field]]
            item[field] = texts if field == 'decisions' else '\n\n'.join(texts)
        # Each selected sentence already carries its qualification beside the claim.
        # Keep account-wide unknowns here without repeating every inline limit.
        item['limits'] = [sentence(i) for i in account['limits']] if protocol else list(dict.fromkeys(universal_limits))
        item['questions'] = list(account['questions'])
        if audit and not protocol:
            checked = next(a for a in audit['arguments']['accounts'] if a['account_id'] == account['id'])
            for lens in checked['lenses']:
                if lens['status'] == 'needs_person':
                    item['questions'].append(lens['next_action'])
                elif lens['status'] != 'supported':
                    item['limits'].append(lens['lens'].replace('_', ' ') + ': ' + lens['finding'] + ' ' + lens['next_action'])
            item['questions'] = list(dict.fromkeys(item['questions']))
        item['sourceRefs'] = list(dict.fromkeys(source_ids[(e['record_id'], e['span_id'])]
            for i in raw['story_order'] if i in selected for e in raw_claims[i]['evidence']))
        accounts.append(item)
    background = list(dict.fromkeys(scope.get('capture_limits', []))) if protocol else []
    if protocol and stop:
        planning = stop.get('planning', {})
        if planning.get('outside_scope_links') or planning.get('unavailable_or_excluded_links'):
            background.append('Some linked originals were outside the selected scope or unavailable in the exports.')
        if any(stop.get('unresolved', {}).values()):
            background.append('Research ended with unresolved source questions.')
    packet = {'schema': 'career-context/v1', 'updatedAt': snapshot, 'reviewStatus': 'draft', 'synthetic': synthetic,
              'person': {'name': scope['subject'], 'overview': '\n\n'.join(sentence(i) for i in plan['overview']), 'background': background},
              'accounts': accounts, 'sources': sources}
    try:
        RENDERER.validate(packet)
    except ValueError as error:
        return None, validation | {'valid': False, 'errors': ['Sheet validation: ' + str(error)]}
    return packet, validation | {'valid': True, 'errors': [], 'sheet_claims': len(claims),
                                'sheet_accounts': len(accounts), 'selected_excerpts': len(sources), 'semantic_checked': False}


def build(workspace, output, force=False):
    if read_json(outside_project(workspace) / 'session.json').get('schema') == 'career-local/v1':
        from local_context import load
        workspace, session, corpus, scope, _ = load(workspace)
    else:
        workspace, session, corpus, scope = load_session(workspace)
    output = outside_project(output)
    if output.suffix.lower() not in {'.html', '.htm'} or not output.parent.is_dir():
        raise ValueError('Choose an HTML file in an existing folder outside the public project.')
    if output.exists() and not force:
        raise ValueError('Output already exists; use --force to replace it.')
    events = events_at(workspace)
    stops = [e for e in events if e['tool'] == 'finish_check' and e['result'].get('allowed')]
    if not stops or events[-1] != stops[-1]:
        raise ValueError('Research needs a current allowed finish receipt before building.')
    stop = stops[-1]
    plans = [e for e in events if e['tool'] == 'sheet_plan' and e['result'].get('valid')]
    if not plans:
        raise ValueError('No checked sheet plan is saved.')
    planned = plans[-1]
    raw = copy.deepcopy(planned['arguments']['review'])
    raw['stop_receipt_id'] = stop['result']['receipt_id']
    records = list(full_records(events).values())
    audit = depth.current_review(events, evidence_version(records, events))
    if session.get('depth_protocol') == depth.PROTOCOL and not audit:
        raise ValueError('This session requires a current depth review before building.')
    if session.get('retention_protocol') == retention.PROTOCOL:
        errors = retention.plan_errors(planned['arguments']['plan'], records, events, spans, challenged=True)
        if errors:
            raise ValueError('This session requires current event retention: ' + '; '.join(errors))
    if session.get('turning_point_protocol') == turning_points.PROTOCOL:
        turning = turning_points.status(events, records, spans)
        if not turning['current']:
            raise ValueError('Turning-point review is incomplete: ' + '; '.join(turning['errors']))
    if planned['result']['evidence_version'] != evidence_version(records, events):
        raise ValueError('Sheet plan is stale for the current evidence.')
    if planned['arguments']['plan'].get('schema') != session.get('export_protocol'):
        raise ValueError('Sheet plan must use the session export protocol; historical journals cannot be silently upgraded.')
    packet, validation = compile_sheet(raw, planned['arguments']['plan'], records, events, scope, corpus['snapshot'], synthetic=corpus['synthetic'])
    if not validation['valid']:
        raise ValueError('Research failed validation: ' + '; '.join(validation['errors']))
    context_path = workspace / 'context.json'
    write_json(context_path, packet)
    result = RENDERER.render(context_path, output)
    write_json(workspace / 'build-receipt.json', {'synthetic': corpus['synthetic'], 'validation': validation,
        'sheet_sha256': result['sha256'], 'checked_draft': draft_hash(raw),
        'journal_sha256': hashlib.sha256((workspace / 'calls.jsonl').read_bytes()).hexdigest(),
        'stop': stop['result']['status'], 'unresolved': stop['result']['unresolved'],
        'source_calls': stop['result']['counts']['source_calls'], 'requests': len(events),
        'depth_protocol': depth.PROTOCOL if audit else 'legacy; no enforced depth review',
        'retention_protocol': session.get('retention_protocol', 'legacy; no section retention'),
        'export_protocol': session.get('export_protocol', 'legacy'),
        'depth_review': audit['result'] if audit else None})
    if session.get('schema') == 'career-local/v1':
        from local_context import status
        status(workspace)
    return result
