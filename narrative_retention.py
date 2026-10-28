"""Keep source events recoverable before choosing the final career narrative.

These are structural and anti-placeholder checks, not a semantic truth grader.
No source access, model calls or filesystem writes occur in this module.
"""
from collections import Counter
import copy
import hashlib
import json
import re

PROTOCOL = 'career-retention/v1'
TEXT = {'type': 'string'}
STATES = ['offered', 'requested', 'planned', 'in_progress', 'completed', 'reported', 'unknown']


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


def array(items, minimum=0, maximum=1000):
    return {'type': 'array', 'items': items, 'minItems': minimum, 'maxItems': maximum}


EVENT = obj({'actor': TEXT, 'action': TEXT, 'state': {'type': 'string', 'enum': STATES},
             'when': TEXT, 'significance': TEXT, 'span_ids': array(TEXT, 1)})
EXTRACTION = obj({'section_id': TEXT, 'finding': TEXT, 'span_ids': array(TEXT),
                  'disposition': {'type': 'string', 'enum': ['events', 'context', 'irrelevant']},
                  'events': array(EVENT), 'reason': TEXT})
SOURCE_KIND = obj({'record_id': TEXT, 'kind': {'type': 'string', 'enum': ['work', 'discussion', 'evaluation']}})
EXTRACTION_SCHEMA = obj({'sections': array(EXTRACTION, 1, 8), 'source_kinds': array(SOURCE_KIND, 0, 8)})
EXTRACTION_SCHEMA['required'] = ['sections']
INVENTORY_SCHEMA = obj({
    'episodes': array(obj({'id': TEXT, 'title': TEXT, 'event_ids': array(TEXT),
        'why_interesting': TEXT, 'disposition': {'type': 'string', 'enum': ['selected', 'reserve']},
        'selection_reason': TEXT}), 1, 80),
    'excluded_events': array(obj({'event_id': TEXT, 'reason': TEXT})),
    'challenge': obj({'reserve_episode_id': TEXT, 'selected_episode_id': TEXT,
                       'comparison': TEXT, 'no_reserve_reason': TEXT}),
})
INVENTORY_SCHEMA['properties']['assignment_mode'] = {'type': 'string', 'enum': ['inline', 'saved']}
ASSIGNMENT_BATCH_SIZE = 100
ASSIGNMENT_PACKET_SIZE = 30
ASSIGNMENT_SCHEMA = obj({'retention_version': TEXT, 'assignments': array(obj({
    'event_id': TEXT, 'episode_id': TEXT, 'exclusion_reason': TEXT}), 1, ASSIGNMENT_BATCH_SIZE)})


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def normal(text):
    return ' '.join(re.findall(r'\w+', text.casefold()))


def specific(text, minimum_words=4):
    """Reject known placeholders; passing never proves meaningful extraction."""
    words = normal(text)
    return len(words.split()) >= minimum_words and not re.search(
        r'reviewed (?:during|as)|documented or participated|no distinct (?:well supported )?episode|'
        r'weaker duplicative contextual|source specific event|^saved source capture|^thread parent message|'
        r'^from .{0,100} time |^source https', words)


def sections(record, span_function):
    """Group exact citation spans without dropping the tail or changing old IDs.

    A source sentence can exceed the target size; it stays intact rather than
    silently truncating evidence or invalidating previously saved citations.
    """
    groups, group, size = [], [], 0
    for span in span_function(record):
        if group and size + len(span['quote']) > 1800:
            groups.append(group)
            group, size = [], 0
        group.append(span)
        size += len(span['quote'])
    if group:
        groups.append(group)
    if not groups:
        groups = [[]]  # An empty original still needs an honest, non-evidential disposition.
    return [{'section_id': record['id'] + '#' + digest(group)[:16], 'record_id': record['id'],
             'ordinal': i + 1, 'total': len(groups), 'citation_spans': group}
            for i, group in enumerate(groups)]


def catalog(records, span_function):
    return {s['section_id']: s for r in records for s in sections(r, span_function)}


def saved_extractions(events, known):
    saved = {}
    for event in events:
        if event['tool'] == 'save_extraction' and event['result'].get('valid'):
            for section in event['arguments']['sections']:
                if section['section_id'] in known:
                    saved[section['section_id']] = section
    return saved


def source_kinds(events):
    kinds = {}
    for event in events:
        if event['tool'] == 'save_extraction' and event['result'].get('valid'):
            for item in event['arguments'].get('source_kinds', []):
                kinds[item['record_id']] = item['kind']
    return kinds


def state(records, events, span_function):
    known = catalog(records, span_function)
    saved = saved_extractions(events, known)
    event_map = {}
    for sid, section in saved.items():
        for i, event in enumerate(section['events']):
            eid = sid + ':' + str(i)
            event_map[eid] = event | {'event_id': eid, 'record_id': known[sid]['record_id'],
                                     'section_id': sid}
    kinds = source_kinds(events)
    components = [known, saved]
    if kinds:
        components.append(kinds)
    return {'known': known, 'saved': saved, 'events': event_map, 'source_kinds': kinds,
            'pending': [sid for sid in known if sid not in saved], 'version': digest(components)}


def validate_extraction(batch, records, events, span_function, classifications=()):
    current = state(records, events, span_function)
    known, saved = current['known'], dict(current['saved'])
    errors, seen = [], set()
    kinds = dict(current['source_kinds'])
    record_ids = {record['id'] for record in records}
    classified = set()
    for item in classifications:
        rid = item['record_id']
        if rid not in record_ids or rid in classified:
            errors.append('Classify each fully read record ID at most once per submission.')
        else:
            kinds[rid] = item['kind']
        classified.add(rid)
    for section in batch:
        sid = section['section_id']
        if sid not in known or sid in seen:
            errors.append('Use each observed cached section ID at most once per submission.')
            continue
        seen.add(sid)
        allowed = {s['span_id'] for s in known[sid]['citation_spans']}
        if known[sid]['record_id'] not in kinds:
            errors.append(sid + ': classify this original as work, discussion or evaluation in source_kinds.')
        if (allowed and not section['span_ids']) or not set(section['span_ids']) <= allowed:
            errors.append(sid + ': finding evidence must come from this exact section.')
        if not allowed and (section['events'] or section['disposition'] == 'events'):
            errors.append(sid + ': an empty original cannot support an event; record context or irrelevance without invented spans.')
        if not specific(section['finding']):
            errors.append(sid + ': replace the header or boilerplate with a concrete finding.')
        if (section['disposition'] == 'events') != bool(section['events']):
            errors.append(sid + ': event disposition requires events; other dispositions cannot hide events.')
        if not section['events'] and not specific(section['reason']):
            errors.append(sid + ': explain the specific context or irrelevance, including why no action is extracted.')
        for event in section['events']:
            if not event['actor'].strip() or not event['when'].strip():
                errors.append(sid + ': identify the actor and event date, or say the date is unknown.')
            if not specific(event['action'], 2) or not specific(event['significance'], 3):
                errors.append(sid + ': preserve a concrete action and why it matters; participation alone is insufficient.')
            if not set(event['span_ids']) <= allowed:
                errors.append(sid + ': event evidence must come from this section.')
        saved[sid] = section
    findings = Counter(normal(s['finding']) for s in saved.values())
    if any(count > 1 for count in findings.values()):
        errors.append('Repeated section findings lose source-specific meaning; state each section’s contribution or distinct context.')
    return {'valid': not errors, 'errors': errors, 'semantic_checked': False}, saved


def notes_from_extractions(records, known, saved, kinds):
    notes = []
    for record in records:
        ids = [sid for sid, s in known.items() if s['record_id'] == record['id']]
        if not ids or any(sid not in saved for sid in ids):
            continue
        parts = [saved[sid] for sid in ids]
        attributions = [{'actor': e['actor'], 'action': e['action'], 'state': e['state'], 'span_ids': e['span_ids']}
                        for s in parts for e in s['events']]
        notes.append({'record_id': record['id'], 'relevance': 'material' if attributions else 'contextual',
            'finding': '\n'.join(s['finding'] for s in parts),
            'span_ids': list(dict.fromkeys(span for s in parts for span in s['span_ids'])),
            'source_kind': kinds[record['id']],
            'attributions': attributions,
            'attribution_limits': 'Extracted from every source section; action states are source reports, not independent verification.'})
    return notes


def saved_assignments(events, version):
    rows = {}
    for event in events:
        if (event['tool'] == 'save_episode_assignments' and event['result'].get('valid')
                and event['result'].get('retention_version') == version):
            rows.update((row['event_id'], row) for row in event['arguments']['assignments'])
    return rows


def assignment_hash(events, version):
    return digest(saved_assignments(events, version))


def assignment_packet(events, current, refs=None):
    stored = saved_assignments(events, current['version'])
    counts = Counter(row['episode_id'] for row in stored.values() if row['episode_id'])
    chosen = refs if refs is not None else [eid for eid in current['events'] if eid not in stored][:ASSIGNMENT_PACKET_SIZE]
    if len(set(chosen)) != len(chosen) or any(eid not in current['events'] for eid in chosen):
        raise ValueError('Use unique, known event IDs when recovering assignments.')
    return {'retention_version': current['version'], 'total': len(current['events']),
            'remaining': len(set(current['events']) - set(stored)),
            'events': [current['events'][eid] | {'saved_assignment': stored.get(eid)} for eid in chosen],
            'episode_counts': dict(sorted(counts.items())[:80]), 'episode_count': len(counts),
            'episode_counts_truncated': len(counts) > 80,
            'excluded_count': sum(not row['episode_id'] for row in stored.values()), 'cache_only': True}


def validate_assignments(args, current):
    errors, seen = [], set()
    if current['pending'] or args['retention_version'] != current['version']:
        errors.append('Finish extraction and use the current retention version before assigning events.')
    for row in args['assignments']:
        eid, episode, reason = row['event_id'], row['episode_id'], row['exclusion_reason']
        if eid not in current['events'] or eid in seen:
            errors.append('Use each known event ID at most once per assignment batch.')
        seen.add(eid)
        if bool(episode) == bool(reason.strip()):
            errors.append('Choose exactly one episode ID or a specific exclusion reason for each event.')
        elif episode and not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', episode):
            errors.append('Episode IDs must be stable safe account IDs.')
        elif not episode and not specific(reason):
            errors.append('Explain the specific evidence being excluded.')
    return {'valid': not errors, 'errors': errors, 'retention_version': current['version'],
            'semantic_checked': False, 'cache_only': True}


def resolve_inventory(inventory, events, current):
    resolved = copy.deepcopy(inventory)
    if resolved.pop('assignment_mode', 'inline') != 'saved':
        return resolved, []
    if any(e['event_ids'] for e in resolved['episodes']) or resolved['excluded_events']:
        return resolved, ['Do not mix inline event IDs or exclusions with saved assignments.']
    rows = saved_assignments(events, current['version'])
    errors = []
    if set(rows) != set(current['events']):
        errors.append('Assign every current event before finalizing the episode inventory.')
    episodes = {episode['id']: episode for episode in resolved['episodes']}
    if any(row['episode_id'] and row['episode_id'] not in episodes for row in rows.values()):
        errors.append('Define every episode named in the saved assignments.')
    for eid, row in rows.items():
        if row['episode_id'] in episodes:
            episodes[row['episode_id']]['event_ids'].append(eid)
        elif not row['episode_id']:
            resolved['excluded_events'].append({'event_id': eid, 'reason': row['exclusion_reason']})
    return resolved, errors


def inventory_hash(event):
    inventory = copy.deepcopy(event['arguments'])
    if inventory.pop('assignment_mode', 'inline') == 'saved':
        return digest([inventory, event['result']['assignments_hash']])
    return digest(inventory)


def inventory_is_current(event, events):
    if event['arguments'].get('assignment_mode') == 'saved':
        return event['result'].get('assignments_hash') == assignment_hash(events, event['result']['retention_version'])
    # Starting a new assignment pass makes an older inline selection provisional.
    after = events[events.index(event) + 1:]
    return not any(e['tool'] == 'save_episode_assignments' and e['result'].get('valid') for e in after)


def validate_inventory(inventory, current):
    errors, assigned, ids = [], [], []
    if current['pending']:
        errors.append('Finish section extraction before ranking episodes.')
    for episode in inventory['episodes']:
        ids.append(episode['id'])
        assigned += episode['event_ids']
        if not episode['event_ids']:
            errors.append('Every defined episode needs at least one retained event.')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', episode['id']):
            errors.append('Episode IDs must be stable safe account IDs.')
        if not specific(episode['why_interesting']) or not specific(episode['selection_reason']):
            errors.append(episode['id'] + ': explain the event sequence and the concrete selection tradeoff.')
    if len(ids) != len(set(ids)):
        errors.append('Episode IDs must be unique.')
    selected = [e for e in inventory['episodes'] if e['disposition'] == 'selected']
    if not 1 <= len(selected) <= 12:
        errors.append('Choose one to twelve selected episodes; keep other episodes in reserve.')
    for item in inventory['excluded_events']:
        assigned.append(item['event_id'])
        if not specific(item['reason']):
            errors.append('Each excluded event needs its own substantive omission reason.')
    if Counter(assigned) != Counter({eid: 1 for eid in current['events']}):
        errors.append('Assign every extracted event exactly once to an episode or a specific exclusion.')
    reasons = [normal(e['selection_reason']) for e in inventory['episodes']]
    reasons += [normal(e['reason']) for e in inventory['excluded_events']]
    if len(reasons) != len(set(reasons)):
        errors.append('Do not use a blanket omission or selection reason for distinct evidence.')
    challenge = inventory['challenge']
    reserves = {e['id'] for e in inventory['episodes'] if e['disposition'] == 'reserve'}
    if reserves:
        if challenge['reserve_episode_id'] not in reserves or challenge['selected_episode_id'] not in {e['id'] for e in selected}:
            errors.append('Compare the strongest reserve episode with one actually selected.')
        if not specific(challenge['comparison']):
            errors.append('Explain why the selected account deserves space over the reserve, or revise selection.')
    elif not specific(challenge['no_reserve_reason']):
        errors.append('Explain why no reserve episode remains, rather than silently discarding alternatives.')
    return {'valid': not errors, 'errors': errors, 'retention_version': current['version'],
            'semantic_checked': False, 'selected_account_ids': [e['id'] for e in selected]}


def latest_inventory(events, current):
    event = next((e for e in reversed(events) if e['tool'] == 'episode_inventory' and e['result'].get('valid')
                  and e['result']['retention_version'] == current['version']), None)
    return event if event and inventory_is_current(event, events) else None


def plan_errors(plan, records, events, span_function, *, challenged=False):
    current = state(records, events, span_function)
    inventory = latest_inventory(events, current)
    errors = []
    if current['pending']:
        errors.append('Review every cached source section before planning or completing the narrative.')
    if not inventory:
        errors.append('Save a current episode_inventory covering every extracted event.')
    else:
        selected = set(inventory['result']['selected_account_ids'])
        if selected != {a['id'] for a in plan['accounts']}:
            errors.append('Sheet accounts must match the selected episode inventory.')
        if challenged:
            first = next((e for e in events if e['tool'] == 'sheet_plan' and e['result'].get('valid')), None)
            if not first or inventory['sequence'] <= first['sequence']:
                errors.append('After the first sheet plan, reconsider the strongest unused episode and resubmit the inventory.')
    return errors
