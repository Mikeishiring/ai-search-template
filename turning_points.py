"""Explicit event-level turning-point review; process checks, not semantic truth."""
import narrative_retention as retention

PROTOCOL = 'career-turning-points/v1'
BATCH_SIZE = 50
KINDS = ['responsibility', 'handoff', 'stopped_work', 'later_use', 'changed_approach', 'not_a_turning_point']
TEXT = retention.TEXT
ROW = retention.obj({'event_id': TEXT, 'kind': {'type': 'string', 'enum': KINDS},
    'account_id': TEXT, 'claim_ids': retention.array(TEXT), 'reason': TEXT})
SAVE_SCHEMA = retention.obj({'review_version': TEXT, 'decisions': retention.array(ROW, 1, BATCH_SIZE)})


def context(events, records, span_function):
    current = retention.state(records, events, span_function)
    inventory = retention.latest_inventory(events, current)
    plan = next((e for e in reversed(events) if e['tool'] == 'sheet_plan' and e['result'].get('valid')), None)
    if current['pending'] or not inventory or not plan:
        raise ValueError('Finish extraction, current episode selection and a checked sheet plan first.')
    resolved, errors = retention.resolve_inventory(inventory['arguments'], events, current)
    if errors:
        raise ValueError('; '.join(errors))
    review, layout = plan['arguments']['review'], plan['arguments']['plan']
    if set(inventory['result']['selected_account_ids']) != {a['id'] for a in layout['accounts']}:
        raise ValueError('Reconcile the sheet plan with the current selected episodes first.')
    # Coverage-note copy alone does not invalidate these event/prose decisions.
    version = retention.digest([current['version'], retention.inventory_hash(inventory), review['claims'], layout])
    origins = {eid: {'episode_id': e['id'], 'disposition': e['disposition']}
               for e in resolved['episodes'] for eid in e['event_ids']}
    origins.update({e['event_id']: {'episode_id': '', 'disposition': 'excluded', 'reason': e['reason']}
                    for e in resolved['excluded_events']})
    return {'version': version, 'events': current['events'], 'origins': origins,
            'claims': {c['id']: c for c in review['claims']}, 'plan': layout}


def saved(events, version):
    rows = {}
    for event in events:
        if (event['tool'] == 'save_turning_points' and event['result'].get('valid')
                and event['arguments']['review_version'] == version):
            rows.update((row['event_id'], row) for row in event['arguments']['decisions'])
    return rows


def supported_claims(event, claims):
    pairs = {(event['record_id'], sid) for sid in event['span_ids']}
    return [cid for cid, c in claims.items() if pairs <= {
        (e['record_id'], e['span_id']) for e in c['evidence']}]


def packet(events, ctx, ids=None):
    reviewed = saved(events, ctx['version'])
    pending = [eid for eid in ctx['events'] if eid not in reviewed]
    chosen = pending[:BATCH_SIZE] if ids is None else ids
    if len(chosen) != len(set(chosen)) or any(eid not in ctx['events'] for eid in chosen):
        raise ValueError('Use unique known event IDs.')
    return {'review_version': ctx['version'], 'total': len(ctx['events']), 'remaining': len(pending),
        'accounts': [{'id': a['id'], 'title': a['title']} for a in ctx['plan']['accounts']],
        'events': [ctx['events'][eid] | {'origin': ctx['origins'][eid],
            'referencing_claim_ids': supported_claims(ctx['events'][eid], ctx['claims']),
            'saved_decision': reviewed.get(eid)} for eid in chosen],
        'instruction': 'Check changing responsibility, handoffs, stopped work, later use and changed approaches. '
            'Connect reserve events to selected accounts where useful. References are pointers, not proof of meaning. '
            'A consequential turning point needs represented prose or a specific reason for omission. '
            'Do not upgrade an announcement to a completed handoff.', 'cache_only': True}


def validate(rows, ctx):
    errors, seen, reasons = [], set(), set()
    fields = ('summary', 'context', 'aim', 'contribution', 'decisions', 'sharedCredit', 'outcome', 'limits')
    accounts = {a['id']: {cid for f in fields for cid in a.get(f, [])} for a in ctx['plan']['accounts']}
    for row in rows:
        eid = row['event_id']
        if eid not in ctx['events'] or eid in seen:
            errors.append('Review each known event at most once per batch.')
            continue
        seen.add(eid)
        reason = retention.normal(row['reason'])
        if not retention.specific(row['reason']) or reason in reasons:
            errors.append('Give each event a substantive, distinct selection or non-turning-point reason.')
        reasons.add(reason)
        aid, cids = row['account_id'], row['claim_ids']
        if aid and aid not in accounts:
            errors.append('A connection must name a currently selected account.')
        if len(cids) != len(set(cids)) or not set(cids) <= accounts.get(aid, set()):
            errors.append('Represented claims must belong to the connected account.')
        if cids and not set(cids) <= set(supported_claims(ctx['events'][eid], ctx['claims'])):
            errors.append('A represented turning point needs a claim retaining every supporting event span.')
        if row['kind'] == 'not_a_turning_point' and (aid or cids):
            errors.append('Non-turning-point decisions cannot claim a narrative connection.')
        if row['kind'] != 'not_a_turning_point' and not aid:
            errors.append('Compare this turning point with a selected account, even when omitting it.')
    return errors


def status(events, records, span_function):
    try:
        ctx = context(events, records, span_function)
    except ValueError as error:
        return {'protocol': PROTOCOL, 'current': False, 'errors': [str(error)]}
    rows = saved(events, ctx['version'])
    errors = validate(list(rows.values()), ctx)
    remaining = len(set(ctx['events']) - set(rows))
    if remaining:
        errors.append(f'Review {remaining} remaining events for turning points, including reserve material.')
    return {'protocol': PROTOCOL, 'current': not errors, 'errors': errors,
            'review_version': ctx['version'], 'decisions_hash': retention.digest(rows),
            'reviewed': len(rows), 'remaining': remaining, 'semantic_checked': False}
