"""Research-to-sheet MCP using fixed fictional sources and a durable local journal."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from research_sheet import (EXPERIMENTS, CURRENT_PLAN_SCHEMA, compile_sheet, digest, plan_schema,
                            draft_hash, evidence_version, load_session)
import autonomous_server as base
from mcp_server import check
from ownership_server import OwnershipSource, TOOLS as RESEARCH_TOOLS, DRAFT_SCHEMA, saved_notes
from completion_server import spans
import depth_protocol as depth
import narrative_retention as retention

TOOLS = copy.deepcopy(RESEARCH_TOOLS) + [base.tool(
    'sheet_plan',
    'Validate and save the complete checked review plus its sheet layout. Field values select claim IDs; no second prose rewrite. '
    'Every claim must appear in an account. Give each detail claim one field; limits select supported claim IDs. '
    'Use questions only for missing facts or personal meaning. Audit notes stay in the journal. Free local operation.',
    {'review': DRAFT_SCHEMA, 'plan': CURRENT_PLAN_SCHEMA}, ['review', 'plan'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False

TOOLS += [base.tool('extraction_packet',
    'Recover up to eight unreviewed sections from fully read cached originals. Extract each section before choosing stories. '
    'No source access or charge. Omit section_ids for the next unreviewed sections.',
    {'section_ids': retention.array(retention.TEXT, 1, 8)}, []),
    base.tool('save_extraction',
    'Save concrete events or specific context for each cached section. Preserve actor, action, date, state, significance '
    'and exact evidence. The host derives durable record notes only after all its sections are reviewed. '
    'Classify each original once in source_kinds as work, discussion or evaluation; reuse that classification across batches. '
    'Empty originals need a context disposition with no spans or events. '
    'Header copies, repeated generic findings and participation placeholders are rejected.',
    retention.EXTRACTION_SCHEMA['properties'], retention.EXTRACTION_SCHEMA['required']),
    base.tool('episode_packet',
    'Recover the extracted event inventory in pages of 30 and the last episode selection. Cache only. '
    'Use these events to connect need, action, reaction, correction and later outcome before ranking stories.',
    {'offset': {'type': 'integer', 'minimum': 0}}, []),
    base.tool('episode_inventory',
    'Keep every extracted event in a selected or reserve episode, or give its specific exclusion. '
    'Choose stable episode IDs matching sheet accounts. Compare the strongest reserve with a selected account. '
    'After the first sheet plan, reconsider and resubmit this inventory before depth_review.',
    retention.INVENTORY_SCHEMA['properties'], retention.INVENTORY_SCHEMA['required'])]
for definition in TOOLS:
    if definition['name'] in {'save_extraction', 'episode_inventory'}:
        definition['annotations']['readOnlyHint'] = False
PLAN_TOOL = next(t for t in TOOLS if t['name'] == 'sheet_plan')
TOOLS += [base.tool('research_probe',
    'Investigate a consequential question within selected sources. Uses the same bounded search and pagination; '
    'saves the account, depth lens, question and actual search receipt. Read returned originals before judging them. '
    'Use at least two lenses before drafting and a fresh contrary-evidence, ownership or later-outcome probe after the first draft.',
    depth.PROBE_PROPERTIES | {'cursor': {'type': 'string'}}, list(depth.PROBE_PROPERTIES)),
    base.tool('depth_review',
    'After sheet_plan, review all ten lenses per account, every material actor/action and the proposed through-line. '
    'Compare each prose clause with the saved actor, action and state, including collective actors. '
    'Reference real probe sequence numbers. Preserve gaps. This validates process and references, not semantic truth. '
    'New evidence, notes or changed prose/layout invalidate the review.',
    depth.REVIEW_SCHEMA['properties'], depth.REVIEW_SCHEMA['required'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False


class SheetSource(OwnershipSource):
    source_budget = depth.SOURCE_BUDGET
    request_limit = depth.REQUEST_LIMIT
    tool_definitions = TOOLS
    local_tools = OwnershipSource.local_tools | {'depth_review', 'extraction_packet', 'save_extraction',
                                                'episode_packet', 'episode_inventory'}

    def __init__(self, corpus, scope, log, *, retention_required=True, export_protocol=None):
        super().__init__(corpus, scope, log)
        self.retention_required = retention_required
        self.configure_export(export_protocol)

    def configure_export(self, protocol):
        self.export_protocol = protocol
        self.tool_definitions = copy.deepcopy(TOOLS)
        definition = next(t for t in self.tool_definitions if t['name'] == 'sheet_plan')
        definition['inputSchema']['properties']['plan'] = copy.deepcopy(plan_schema(protocol))

    def accessible(self, record):
        return (super().accessible(record) and record['source'] in self.scope['sources']
                and record.get('container') not in self.scope.get('excluded_containers', []))

    def dispatch(self, name, args):
        if 'source' in args and args['source'] not in self.scope['sources']:
            raise ValueError('Source outside selected scope')
        if name == 'read_attachment' and not any(
                self.accessible(r) and args['id'] in r.get('attachments', []) for r in self.records.values()):
            raise ValueError('Attachment outside selected scope')
        if name == 'research_probe':
            if not all(args[k].strip() for k in ('account_id', 'question', 'query')):
                raise ValueError('Give a specific account, question and search.')
            return super().dispatch('search', {k: v for k, v in args.items() if k in {'source', 'query', 'cursor'}})
        result = super().dispatch(name, args)
        if name == 'source_inventory':
            result['sources'] = [s for s in result['sources'] if s['id'] in self.scope['sources']]
        return result

    def decorate(self, result):
        super().decorate(result)
        # The next journal sequence is the receipt ID returned to the agent.
        result['sequence'] = len(self.events) + 1
        if 'notes' in result and 'counts' in result:
            result['probe_receipts'] = self.probe_receipts()

    def probe_receipts(self):
        return [{'sequence': e['sequence'], 'account_id': e['arguments']['account_id'],
                 'lens': e['arguments']['lens'], 'source': e['arguments']['source'],
                 'query': e['arguments']['query'], 'cache_hit': e['result'].get('cache_hit', False)}
                for e in self.events if e['tool'] == 'research_probe' and not e['result'].get('error')]

    def cached(self, name, args):
        if name == 'research_probe':
            # Relabelling a cached query does not create another challenge pass.
            query = {k: v for k, v in args.items() if k in {'source', 'query', 'cursor'}}
            for e in self.events:
                if e['tool'] not in {'search', 'research_probe'} or e['result'].get('error'):
                    continue
                previous = {k: v for k, v in e['arguments'].items() if k in {'source', 'query', 'cursor'}}
                if query == previous and e['arguments'].get('window', 'all') == 'all':
                    return {k: copy.deepcopy(v) for k, v in e['result'].items()
                            if k not in {'planning', 'remaining_calls', 'cache_hit', 'source_charge'}}
            return None
        return super().cached(name, args)

    def local(self, name, args):
        if name in {'extraction_packet', 'save_extraction', 'episode_packet', 'episode_inventory'}:
            records = list(self.full_reads().values())
            current = retention.state(records, self.events, spans)
            if name == 'extraction_packet':
                ids = args.get('section_ids', current['pending'][:8])
                if any(sid not in current['known'] for sid in ids):
                    raise ValueError('Only observed sections from full cached reads are available.')
                by_id = {r['id']: r for r in records}
                return {'sections': [current['known'][sid] | {'source': {
                    k: by_id[current['known'][sid]['record_id']][k] for k in ('id', 'date', 'author', 'title')},
                    'saved': current['saved'].get(sid),
                    'source_kind': current['source_kinds'].get(current['known'][sid]['record_id']),
                    'empty_original': not current['known'][sid]['citation_spans']} for sid in ids],
                    'remaining_sections': len(current['pending']), 'cache_only': True}
            if name == 'save_extraction':
                result, saved = retention.validate_extraction(args['sections'], records, self.events, spans, args.get('source_kinds', []))
                if result['valid']:
                    affected = {current['known'][s['section_id']]['record_id'] for s in args['sections']}
                    classifications = {item['record_id']: item['kind'] for item in args.get('source_kinds', [])}
                    affected.update(classifications)
                    result['notes'] = retention.notes_from_extractions(
                        [r for r in records if r['id'] in affected], current['known'], saved,
                        current['source_kinds'] | classifications)
                return result
            if name == 'episode_packet':
                items = list(current['events'].values())
                offset = args.get('offset', 0)
                prior = retention.latest_inventory(self.events, current)
                return {'events': items[offset:offset + 30], 'total': len(items),
                        'next_offset': offset + 30 if offset + 30 < len(items) else None,
                        'inventory': prior['arguments'] if prior else None, 'cache_only': True}
            return retention.validate_inventory(args, current)
        if name == 'depth_review':
            records = list(self.full_reads().values())
            result = depth.validate_review(args, self.events, records, saved_notes(self.events), self.scope,
                                           evidence_version(records, self.events), spans)
            if self.retention_required:
                plan = depth.latest_plan(self.events)
                if plan:
                    result['errors'] += retention.plan_errors(plan['arguments']['plan'], records, self.events, spans, challenged=True)
                inventory = retention.latest_inventory(self.events, retention.state(records, self.events, spans))
                result['inventory_hash'] = retention.digest(inventory['arguments']) if inventory else None
                result['valid'] = not result['errors']
            if not result['valid']:
                result['available_probe_receipts'] = self.probe_receipts()
            return result
        return super().local(name, args)

    def planning(self):
        result = super().planning()
        outside = [r for r in result['unread_references'] if r['source'] not in self.scope['sources']]
        result['outside_scope_links'] = outside
        result['unread_references'] = [r for r in result['unread_references'] if r not in outside]
        plans = [e for e in self.events if e['tool'] == 'sheet_plan' and e['result'].get('valid')]
        version = evidence_version(list(self.full_reads().values()), self.events)
        result['writing']['export_protocol'] = self.export_protocol or 'legacy'
        result['writing']['sheet_plan_current'] = bool(plans and plans[-1]['result']['evidence_version'] == version)
        review = depth.current_review(self.events, version)
        result['depth'] = {'protocol': depth.PROTOCOL, 'review_current': bool(review),
                          'lenses': list(depth.LENSES), 'source_budget': self.source_budget,
                          'request_limit': self.request_limit,
                          'pending_research': review['result']['pending_research'] if review else [],
                          'next_step': 'Resolve pending research or finish_check.' if review else
                          'Investigate, draft, challenge the draft with a new probe, revise and plan, then depth_review.'}
        result['calls_remaining'] = self.source_budget - self.source_calls()
        result['earlier_start'] = self.scope.get('earlier_start', result['earlier_start'])
        if self.retention_required:
            current = retention.state(list(self.full_reads().values()), self.events, spans)
            result['writing']['recovery'] = ('extraction_packet, save_extraction and episode_packet recover cached '
                'evidence without a source charge, within the total request ceiling. save_notes is disabled.')
            result['retention'] = {'protocol': retention.PROTOCOL, 'sections': len(current['known']),
                'reviewed_sections': len(current['saved']), 'pending_sections': len(current['pending']),
                'events': len(current['events']), 'inventory_current': bool(retention.latest_inventory(self.events, current)),
                'next_step': 'extraction_packet, save_extraction, episode_packet, then episode_inventory before drafting.'}
        return result

    def finish(self):
        result = super().finish()
        if self.retention_required:
            plan = depth.latest_plan(self.events)
            errors = retention.plan_errors(plan['arguments']['plan'] if plan else {'accounts': []},
                list(self.full_reads().values()), self.events, spans, challenged=True)
            if errors:
                result['unresolved']['retention'] = errors
                result.update(allowed=False, status='retain_evidence', receipt_id=None)
                return result
        if not self.planning()['writing']['sheet_plan_current']:
            result.update(allowed=False, status='plan_sheet', receipt_id=None)
        else:
            review = depth.current_review(self.events, evidence_version(list(self.full_reads().values()), self.events))
            if not review:
                result.update(allowed=False, status='review_depth', receipt_id=None)
            else:
                pending = review['result']['pending_research']
                result['unresolved']['depth_questions'] = pending
                if pending:
                    capped = self.source_calls() >= self.source_budget or len(self.events) + 1 >= self.request_limit
                    result.update(allowed=result['allowed'] and capped, status='depth_budget_limit' if capped else 'continue_depth', receipt_id=None)
        if result['allowed']:
            result['receipt_id'] = base.digest([result, [(e['sequence'], e['tool'], e['arguments']) for e in self.events]])
        return result

    def execute(self, name, args):
        # A sealed journal can be rebuilt repeatedly, but cannot silently acquire new evidence.
        if self.events and self.events[-1]['tool'] == 'finish_check' and self.events[-1]['result'].get('allowed'):
            return {'error': 'session_sealed', 'instruction': 'Build the checked sheet from this saved journal.'}
        if name == 'save_notes' and self.retention_required:
            return {'error': 'section_extraction_required',
                    'instruction': 'Use extraction_packet and save_extraction; durable notes are derived from all sections.'}
        if name != 'sheet_plan':
            return super().execute(name, args)
        definition = next(t for t in self.tool_definitions if t['name'] == 'sheet_plan')
        check(args, definition['inputSchema'])
        if len(self.events) >= self.request_limit:
            return {'error': 'request_limit_exhausted'}
        records = list(self.full_reads().values())
        _, validation = compile_sheet(args['review'], args['plan'], records, self.events,
                                      self.scope, self.corpus['snapshot'], draft=True, synthetic=self.corpus['synthetic'])
        current = evidence_version(records, self.events)
        if self.retention_required:
            validation['errors'] += retention.plan_errors(args['plan'], records, self.events, spans)
            validation['valid'] = not validation['errors']
        for account in args['plan']['accounts']:
            lenses = {e['arguments']['lens'] for e in self.events if e['tool'] == 'research_probe'
                      and e['arguments']['account_id'] == account['id'] and not e['result'].get('error')}
            if len(lenses) < 2:
                validation['errors'].append(account['id'] + ': investigate two different depth questions before planning this account.')
                validation['valid'] = False
        if not any(e['tool'] == 'draft_check' and e['result'].get('valid')
                   and e['result'].get('draft_hash') == draft_hash(args['review'])
                   and e['result'].get('evidence_version') == current for e in self.events):
            validation['errors'].append('Run draft_check on this review and current evidence before planning the sheet.')
            validation['valid'] = False
        result = {'valid': validation['valid'], 'errors': validation['errors'],
                  'draft_hash': draft_hash(args['review']), 'evidence_version': evidence_version(records, self.events),
                  'plan_hash': digest(args['plan']), 'semantic_checked': False, 'source_charge': 0}
        event = {'sequence': len(self.events) + 1, 'tool': name, 'arguments': args, 'result': result,
                 'source_charge': 0, 'observed_at': datetime.now(timezone.utc).isoformat()}
        self.events.append(event)
        result['planning'] = self.planning()
        with self.path.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + '\n')
        return result


class LocalSheetSource(SheetSource):
    """Selected local captures; never relabel personal records as synthetic."""
    def __init__(self, corpus, scope, log, policy, *, retention_required=True, export_protocol=None):
        self.corpus, self.scope, self.path, self.policy = corpus, scope, log, policy
        self.policy_path = log.parent / 'policy.json'
        self.policy_digest = digest(policy)
        self.records = {r['id']: r for r in corpus['records']}
        self.events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
        self.retention_required = retention_required
        self.configure_export(export_protocol)

    def execute(self, name, args):
        # Revocation also blocks an already-running server and cache recovery.
        try:
            current = json.loads(self.policy_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'error': 'policy_unavailable', 'instruction': 'Stop research and restore or reconfigure the local policy.'}
        if digest(current) != self.policy_digest:
            return {'error': 'policy_changed', 'instruction': 'Stop research. Changed settings require a newly validated session.'}
        return super().execute(name, args)

    def accessible(self, record):
        from local_context import permitted
        return permitted(self.policy, record)

    def dispatch(self, name, args):
        if name == 'source_inventory':
            result = super().dispatch(name, args)
            result.update(synthetic=False, privacy={k: self.policy[k] for k in (
                'locations', 'allow_dms', 'allow_private_channels', 'allow_attachments',
                'retain_source_text', 'model_processing')})
            return result
        if name == 'list_roots' and args['window'] == 'earlier':
            rows = [r for r in self.records.values() if r['source'] == args['source'] and self.accessible(r)]
            active = {self.root(r)['id'] for r in rows if self.scope['earlier_start'] <= r['date'] < self.scope['start']}
            return self.page(name, args, [r for r in rows if r['id'] in active and (not args.get('container') or r['container'] == args['container'])])
        return super().dispatch(name, args)

    def planning(self):
        result = super().planning()
        # A pointer into an unimported location remains a known gap, never an implicit grant.
        blocked = [ref for ref in result['unread_references'] if ref['id'] not in self.records]
        result['unread_references'] = [ref for ref in result['unread_references'] if ref not in blocked]
        result['unavailable_or_excluded_links'] = blocked
        return result


def serve(workspace):
    # MCP JSON is UTF-8 even when the Windows console code page differs.
    sys.stdin.reconfigure(encoding='utf-8')
    sys.stdout.reconfigure(encoding='utf-8')
    from research_sheet import outside_project, read_json
    workspace = outside_project(workspace)
    local = read_json(workspace / 'session.json').get('schema') == 'career-local/v1'
    if local:
        from local_context import load
        workspace, _, corpus, scope, policy = load(workspace, for_model=True)
    else:
        workspace, _, corpus, scope = load_session(workspace)
    log = (workspace / 'calls.jsonl').resolve()
    session = read_json(workspace / 'session.json')
    required = session.get('retention_protocol') == retention.PROTOCOL
    options = {'retention_required': required, 'export_protocol': session.get('export_protocol')}
    server = LocalSheetSource(corpus, scope, log, policy, **options) if local else SheetSource(corpus, scope, log, **options)
    schemas = {(EXPERIMENTS / ('model/' + name + '.schema.json')).resolve()
               for name in ['ownership', 'retention', 'depth', 'completion', 'attribution', 'review']}
    if local:
        schemas.add((workspace / 'policy.json').resolve())
    base.TOOLS = copy.deepcopy(server.tool_definitions)
    if local:
        for definition in base.TOOLS:
            definition['description'] = definition['description'].replace('synthetic', 'selected local')
    base.guard(schemas, log)
    for line in sys.stdin:
        try:
            reply = base.respond(json.loads(line), server)
            if local and reply and 'serverInfo' in reply.get('result', {}):
                reply['result']['serverInfo']['name'] = 'career_context_local'
        except (ValueError, TypeError):
            reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}
        if reply is not None:
            print(json.dumps(reply), flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: research_sheet_server.py WORKSPACE')
    serve(Path(sys.argv[1]))
