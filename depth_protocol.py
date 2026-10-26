"""Receipt-backed depth review. Validates the review process, never semantic truth."""
from collections import Counter

PROTOCOL = 'career-depth/v1'
SOURCE_BUDGET = 450
REQUEST_LIMIT = 800
LENSES = ('origins', 'stakes', 'personal_decisions', 'shared_ownership', 'implementation',
          'setbacks', 'later_outcomes', 'contrary_evidence', 'personal_meaning', 'trajectory')
STATUSES = ('supported', 'limited', 'needs_person', 'out_of_scope', 'pending')
TEXT = {'type': 'string'}


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def array(items, minimum=0, maximum=1000):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


EVIDENCE = obj({'record_id': TEXT, 'span_id': TEXT})
PROBE_PROPERTIES = {'account_id': TEXT, 'lens': {'type': 'string', 'enum': list(LENSES)},
                    'question': TEXT, 'source': {'type': 'string', 'enum': ['chat', 'docs', 'repo']}, 'query': TEXT}
REVIEW_SCHEMA = obj({
    'accounts': array(obj({'account_id': TEXT, 'lenses': array(obj({
        'lens': {'type': 'string', 'enum': list(LENSES)},
        'status': {'type': 'string', 'enum': list(STATUSES)},
        'finding': TEXT, 'counterpoint': TEXT, 'next_action': TEXT,
        'evidence': array(EVIDENCE), 'claim_ids': array(TEXT),
        'probe_sequences': array({'type': 'integer', 'minimum': 1}),
    }), len(LENSES), len(LENSES))}), 1, 12),
    'attribution_coverage': array(obj({'record_id': TEXT,
        'attribution_index': {'type': 'integer', 'minimum': 0},
        'claim_ids': array(TEXT), 'omission_reason': TEXT})),
    'through_line': obj({'status': {'type': 'string', 'enum': ['pattern', 'single_episode', 'insufficient']},
        'account_ids': array(TEXT), 'claim_ids': array(TEXT), 'interpretation': TEXT, 'exception_or_limit': TEXT}),
})


def latest_plan(events):
    return next((e for e in reversed(events) if e['tool'] == 'sheet_plan' and e['result'].get('valid')), None)


def latest_review(events):
    return next((e for e in reversed(events) if e['tool'] == 'depth_review' and e['result'].get('valid')), None)


def current_review(events, version):
    plan, review = latest_plan(events), latest_review(events)
    if not plan or not review:
        return None
    expected = (version, plan['result']['draft_hash'], plan['result']['plan_hash'])
    actual = tuple(review['result'].get(k) for k in ('evidence_version', 'draft_hash', 'plan_hash'))
    return review if actual == expected and plan['result']['evidence_version'] == version else None


def validate_review(audit, events, records, notes, scope, version, span_function):
    """Check real searches, complete lenses, attribution-level accounting and current prose."""
    plan_event = latest_plan(events)
    errors = []
    if not plan_event or plan_event['result']['evidence_version'] != version:
        return {'valid': False, 'errors': ['Save a sheet_plan for the current checked draft and evidence first.']}
    plan, review = plan_event['arguments']['plan'], plan_event['arguments']['review']
    accounts = {a['id']: a for a in plan['accounts']}
    claims = {c['id']: c for c in review['claims']}
    fields = ('summary', 'context', 'aim', 'contribution', 'decisions', 'sharedCredit', 'outcome')
    catalog = {(r['id'], s['span_id']) for r in records for s in span_function(r)}
    probes = {e['sequence']: e for e in events if e['tool'] == 'research_probe'
              and not e['result'].get('error')}
    pending = []
    if Counter(a['account_id'] for a in audit['accounts']) != Counter({a: 1 for a in accounts}):
        errors.append('Review every planned account exactly once.')
    for account in audit['accounts']:
        aid = account['account_id']
        if aid not in accounts:
            continue
        allowed_claims = {cid for field in fields for cid in accounts[aid][field]}
        covered = set()
        if Counter(l['lens'] for l in account['lenses']) != Counter(LENSES):
            errors.append(aid + ': review each depth lens exactly once.')
        # Questions must actually be investigated, not just written into a checklist.
        first_draft = next((e['sequence'] for e in events if e['tool'] == 'sheet_plan' and e['result'].get('valid')
                            and any(a['id'] == aid for a in e['arguments']['plan']['accounts'])), None)
        attempted = [e for e in probes.values() if e['arguments']['account_id'] == aid]
        before = [e for e in attempted if first_draft and e['sequence'] < first_draft]
        after = [e for e in attempted if first_draft and e['sequence'] > first_draft
                 and e['arguments']['lens'] in {'shared_ownership', 'later_outcomes', 'contrary_evidence'}
                 and not e['result'].get('cache_hit')]
        if len({e['arguments']['lens'] for e in before}) < 2:
            errors.append(aid + ': investigate at least two different depth questions before its first sheet plan.')
        if not set(scope['sources']) <= {e['arguments']['source'] for e in attempted}:
            errors.append(aid + ': investigate the account across every selected source group, including no-result searches.')
        if not after:
            errors.append(aid + ': after its first sheet plan, investigate an alternative explanation, ownership or later outcome with a new query.')
        for lens in account['lenses']:
            label = aid + '/' + lens['lens']
            ids = set(lens['claim_ids'])
            covered |= ids
            if not ids <= allowed_claims:
                errors.append(label + ': claims must belong to this account.')
            pairs = {(e['record_id'], e['span_id']) for e in lens['evidence']}
            if not pairs <= catalog:
                errors.append(label + ': evidence must use exact spans from full reads.')
            if not lens['finding'].strip() or not lens['counterpoint'].strip():
                errors.append(label + ': explain the finding and its counterpoint or limit.')
            if lens['status'] == 'supported' and (not pairs or not ids):
                errors.append(label + ': supported findings need evidence and represented claims.')
            claim_pairs = {(e['record_id'], e['span_id']) for cid in ids if cid in claims for e in claims[cid]['evidence']}
            if ids and not pairs & claim_pairs:
                errors.append(label + ': reviewed claims must cite some of the selected evidence.')
            for seq in lens['probe_sequences']:
                if seq not in probes or probes[seq]['arguments']['account_id'] != aid:
                    errors.append(label + ': probe receipts must come from this account.')
            if not pairs and lens['status'] != 'out_of_scope' and not lens['probe_sequences']:
                errors.append(label + ': a gap needs a real attempted search, not an untested assumption.')
            if lens['status'] != 'supported' and not lens['next_action'].strip():
                errors.append(label + ': record the remaining question or boundary.')
            if lens['status'] == 'pending':
                pending.append({'account_id': aid, 'lens': lens['lens'], 'next_action': lens['next_action']})
        if covered != allowed_claims:
            errors.append(aid + ': every narrative claim needs depth review.')

    # Record-level coverage was too coarse: one citation could hide another person's contribution.
    required = {(rid, i) for rid, note in notes.items() if note['relevance'] == 'material'
                for i in range(len(note['attributions']))}
    seen = set()
    for item in audit['attribution_coverage']:
        key = item['record_id'], item['attribution_index']
        if key not in required or key in seen:
            errors.append('Unknown or duplicate material attribution in depth review.')
        seen.add(key)
        if not item['claim_ids'] and not item['omission_reason'].strip():
            errors.append('Every material actor/action needs narrative credit or an explicit omission reason.')
        for cid in item['claim_ids']:
            refs = {(r['record_id'], r['attribution_index']) for r in claims.get(cid, {}).get('roles', [])}
            if key not in refs:
                errors.append('Attribution coverage must point to a claim carrying that exact saved actor/action.')
    if seen != required:
        errors.append('Account for every material actor/action, not only every source record.')

    line = audit['through_line']
    aids, cids = set(line['account_ids']), set(line['claim_ids'])
    if not aids <= set(accounts) or not cids <= set(claims):
        errors.append('The through-line may reference only planned accounts and checked claims.')
    if not line['interpretation'].strip() or not line['exception_or_limit'].strip():
        errors.append('Explain the proposed through-line and its exception or evidential limit.')
    if line['status'] == 'pattern' and len(aids) < 2:
        errors.append('One episode cannot establish a cross-episode pattern.')
    if line['status'] == 'single_episode' and len(aids) != 1:
        errors.append('An episode-level observation needs exactly one account.')
    if line['status'] != 'insufficient':
        for aid in aids & set(accounts):
            if not cids & {cid for f in fields for cid in accounts[aid][f]}:
                errors.append('Ground the through-line in a checked claim from each selected account.')
    return {'valid': not errors, 'errors': errors, 'protocol': PROTOCOL,
            'evidence_version': version, 'draft_hash': plan_event['result']['draft_hash'],
            'plan_hash': plan_event['result']['plan_hash'], 'pending_research': pending,
            'reviewed_accounts': len(audit['accounts']), 'attributions_accounted_for': len(seen & required),
            'semantic_checked': False, 'reviewer': 'researching_agent', 'independent_review': False}
