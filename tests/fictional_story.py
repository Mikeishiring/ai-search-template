"""Small fictional observatory journal used by interruption and selection tests."""
import copy
import local_context
import depth_protocol as depth
from research_sheet import write_json, EXPORT_PROTOCOL, FIELDS
from research_sheet_server import LocalSheetSource
from completion_server import spans


def initialize(folder):
    export = folder / 'fictional-export.json'
    records = [{'id': 'docs:mirror', 'body': 'I built a mirror checklist after three alignment faults.'},
               {'id': 'docs:rota', 'body': 'I announced that Contributor 02 would take over the night rota while I focused on mirror alignment.'}]
    for r in records:
        r.update(source='docs', container='observatory', kind='document', author='Contributor 01',
                 date='2034-02-10', title=r['id'], parent=None, links=[], attachments=[])
    write_json(export, {'records': records, 'attachments': []})
    policy = {'subject': 'Contributor 01', 'question': 'Understand observatory calibration',
        'earlier_start': '2034-01-01', 'start': '2034-02-01', 'end': '2034-03-31', 'horizon': '2034-05-31',
        'locations': [{'source': 'docs', 'container': 'observatory', 'kind': 'document'}],
        'import_files': [str(export)], 'allow_dms': False, 'allow_private_channels': False,
        'allow_attachments': False, 'retain_source_text': True, 'model_processing': 'selected_sources'}
    workspace = folder / 'workspace'
    local_context.initialize(workspace, policy)
    local_context.import_export(workspace, export)
    return workspace


def source(workspace):
    workspace, session, corpus, scope, policy = local_context.load(workspace, for_model=True)
    return LocalSheetSource(corpus, scope, workspace / 'calls.jsonl', policy,
                            export_protocol=session['export_protocol'], turning_required=True)


def call(server, name, args):
    result = server.execute(name, args)
    assert not result.get('error') and result.get('valid') is not False, (name, result)
    return result


def prepare(server):
    for window in ['earlier', 'primary', 'followup']:
        call(server, 'list_roots', {'source': 'docs', 'window': window})
    for lens, query in [('origins', 'mirror'), ('shared_ownership', 'rota')]:
        call(server, 'research_probe', {'source': 'docs', 'query': query, 'account_id': 'calibration',
            'lens': lens, 'question': 'What does the observatory record establish?'})
    for r in server.corpus['records']:
        call(server, 'read_record', {'source': 'docs', 'id': r['id']})
    sections = call(server, 'extraction_packet', {})['sections']
    rows = []
    for section in sections:
        r = server.records[section['record_id']]
        refs = [s['span_id'] for s in section['citation_spans']]
        rows.append({'section_id': section['section_id'], 'finding': r['body'], 'span_ids': refs,
            'disposition': 'events', 'reason': '', 'events': [{'actor': 'Contributor 01',
                'action': r['body'], 'state': 'reported', 'when': r['date'],
                'significance': 'A concrete observatory action is reported; later effects remain unmeasured.', 'span_ids': refs}]})
    call(server, 'save_extraction', {'sections': rows, 'source_kinds': [
        {'record_id': r['id'], 'kind': 'work'} for r in server.corpus['records']]})
    events = call(server, 'episode_packet', {})['events']
    inventory = {'episodes': [
        {'id': 'calibration', 'title': 'Mirror calibration', 'event_ids': [events[0]['event_id']],
         'why_interesting': 'Alignment faults prompted a concrete written checklist.', 'disposition': 'selected',
         'selection_reason': 'The checklist is a reported response to alignment faults.'},
        {'id': 'rota', 'title': 'Rota handoff', 'event_ids': [events[1]['event_id']],
         'why_interesting': 'A rota announcement may explain a change in calibration responsibility.', 'disposition': 'reserve',
         'selection_reason': 'The handoff announcement lacks evidence of completed transfer.'}],
        'excluded_events': [], 'challenge': {'reserve_episode_id': 'rota', 'selected_episode_id': 'calibration',
         'comparison': 'The rota announcement explains focus but cannot establish a completed handoff.', 'no_reserve_reason': ''}}
    call(server, 'episode_inventory', inventory)
    claims = [{'id': 'c' + str(i + 1), 'category': 'contribution', 'statement': r['body'], 'limits': '',
        'evidence': [{'record_id': r['id'], 'span_id': s['span_id']} for s in spans(r)],
        'roles': [{'record_id': r['id'], 'attribution_index': 0}]} for i, r in enumerate(server.corpus['records'])]
    raw = {'claims': claims[:1], 'unknowns': [], 'rejected_conclusions': [], 'stop_receipt_id': 'pending',
           'research_choices': ['Read the two selected fictional originals.'], 'story_order': ['c1'],
           'coverage_notes': [{'record_id': 'docs:rota', 'reason': 'Keep the announced rota handoff in reserve while evaluating its connection.'}]}
    account = {f: [] for f in FIELDS}
    account.update(id='calibration', title='Mirror calibration', period='February 2034',
                   summary=['c1'], contribution=['c1'], limits=[], questions=[])
    plan = {'schema': EXPORT_PROTOCOL, 'overview': ['c1'], 'accounts': [account]}
    call(server, 'draft_check', {'draft': raw})
    call(server, 'sheet_plan', {'review': raw, 'plan': plan})
    return raw, plan, claims, inventory


def complete(server, prepared):
    raw, plan, claims, inventory = copy.deepcopy(prepared)
    raw.update(claims=claims, story_order=['c1', 'c2'], coverage_notes=[])
    plan['accounts'][0]['decisions'] = ['c2']
    call(server, 'draft_check', {'draft': raw})
    call(server, 'sheet_plan', {'review': raw, 'plan': plan})
    call(server, 'research_probe', {'source': 'docs', 'query': 'completed handoff', 'account_id': 'calibration',
        'lens': 'contrary_evidence', 'question': 'Does anything confirm completion of the announced transfer?'})
    call(server, 'episode_inventory', inventory)
    packet = call(server, 'turning_point_packet', {})
    decisions = [{'event_id': e['event_id'], 'kind': 'handoff' if e['record_id'] == 'docs:rota' else 'changed_approach',
        'account_id': 'calibration', 'claim_ids': ['c2' if e['record_id'] == 'docs:rota' else 'c1'],
        'reason': ('The rota announcement explains the intended focus without proving transfer completion.'
                   if e['record_id'] == 'docs:rota' else 'The written checklist responds directly to the reported alignment faults.')}
        for e in packet['events']]
    call(server, 'save_turning_points', {'review_version': packet['review_version'], 'decisions': decisions})
    audit = {'accounts': [{'account_id': 'calibration', 'lenses': [
        {'lens': lens, 'status': 'limited', 'finding': 'Two records describe a checklist and an announced rota handoff.',
         'counterpoint': 'Completed transfer and later impact remain unconfirmed.',
         'next_action': 'Keep this limit; no further selected source establishes it.',
         'evidence': [e for c in claims for e in c['evidence']], 'claim_ids': ['c1', 'c2'], 'probe_sequences': []}
        for lens in depth.LENSES]}],
        'attribution_coverage': [{'record_id': r['id'], 'attribution_index': 0,
            'claim_ids': ['c' + str(i + 1)], 'omission_reason': ''} for i, r in enumerate(server.corpus['records'])],
        'through_line': {'status': 'single_episode', 'account_ids': ['calibration'], 'claim_ids': ['c1', 'c2'],
            'interpretation': 'Written calibration work alongside an announced rota transfer.',
            'exception_or_limit': 'One episode, without proof of transfer completion or measured impact.'}}
    call(server, 'depth_review', audit)
    result = call(server, 'finish_check', {})
    assert result['allowed'], result
    return result
