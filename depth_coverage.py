"""Bounded attribution review, tied to the exact draft, evidence and selection.

Saved rows never supply missing judgments. The final depth validator still
requires every material attribution to have credit or an explicit omission.
"""
import copy

import depth_protocol as depth
import narrative_retention as retention

ITEM = depth.REVIEW_SCHEMA['properties']['attribution_coverage']['items']
REF = depth.obj({'record_id': depth.TEXT, 'attribution_index': {'type': 'integer', 'minimum': 0}})
BATCH_SIZE = 100
SAVE_SCHEMA = depth.obj({'review_version': depth.TEXT,
                        'attribution_coverage': depth.array(ITEM, 1, BATCH_SIZE)})


def key(item):
    return item['record_id'], item['attribution_index']


def context(events, evidence_version, inventory_hash):
    plan = depth.latest_plan(events)
    if not plan or plan['result']['evidence_version'] != evidence_version:
        raise ValueError('Save a sheet plan for the current evidence before reviewing attribution coverage.')
    version = retention.digest([evidence_version, plan['result']['draft_hash'],
                                plan['result']['plan_hash'], inventory_hash])
    return version, plan['arguments']['review']


def saved(events, version):
    rows = {}
    for event in events:
        if (event['tool'] == 'save_attribution_coverage' and event['result'].get('valid')
                and event['result'].get('review_version') == version):
            for row in event['arguments']['attribution_coverage']:
                rows[key(row)] = row
    return rows


def material(notes):
    return {(rid, i): value for rid, note in notes.items() if note['relevance'] == 'material'
            for i, value in enumerate(note['attributions'])}


def packet(events, notes, version, review, refs=None):
    known, stored = material(notes), saved(events, version)
    chosen = [key(ref) for ref in refs] if refs is not None else [k for k in known if k not in stored][:BATCH_SIZE]
    if len(set(chosen)) != len(chosen) or any(k not in known for k in chosen):
        raise ValueError('Use unique, known material attribution references.')
    claims = {}
    for claim in review['claims']:
        for ref in claim['roles']:
            claims.setdefault(key(ref), []).append(claim['id'])
    return {'review_version': version, 'total': len(known), 'remaining': len(set(known) - set(stored)),
            'attributions': [{'record_id': rid, 'attribution_index': i, **known[(rid, i)],
                              'referencing_claim_ids': claims.get((rid, i), []),
                              'saved_review': stored.get((rid, i))} for rid, i in chosen],
            'cache_only': True}


def validate(rows, notes, review):
    known, seen, errors = material(notes), set(), []
    claims = {c['id']: c for c in review['claims']}
    for row in rows:
        ref = key(row)
        if ref not in known or ref in seen:
            errors.append('Use each known material attribution at most once per batch.')
        seen.add(ref)
        if not row['claim_ids'] and not row['omission_reason'].strip():
            errors.append('Give narrative credit or an explicit omission reason for each attribution.')
        for cid in row['claim_ids']:
            if ref not in {key(r) for r in claims.get(cid, {}).get('roles', [])}:
                errors.append('Credit must reference a claim carrying that exact saved actor/action.')
    return errors


def combine(events, version, inline):
    # Preserve duplicates here: the existing full validator must reject overlap
    # between explicit inline rows and saved batches, rather than guess intent.
    return [copy.deepcopy(row) for _, row in sorted(saved(events, version).items())] + copy.deepcopy(inline)


def coverage_hash(events, version, inline):
    return retention.digest(combine(events, version, inline))


def contributing_sequences(events, version):
    latest = {}
    for event in events:
        if (event['tool'] == 'save_attribution_coverage' and event['result'].get('valid')
                and event['result'].get('review_version') == version):
            for row in event['arguments']['attribution_coverage']:
                latest[key(row)] = event['sequence']
    return sorted(set(latest.values()))
