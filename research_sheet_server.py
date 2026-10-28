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
import depth_coverage
import turning_points

TOOLS = copy.deepcopy(RESEARCH_TOOLS) + [base.tool(
    'sheet_plan',
    'Validate and save the complete checked review plus its sheet layout. Field values select claim IDs; no second prose rewrite. '
    'Every claim must appear in an account. Give each detail claim one field; limits select supported claim IDs. '
    'Use questions only for missing facts or personal meaning. Audit notes stay in the journal. Free local operation.',
    {'review': DRAFT_SCHEMA, 'plan': CURRENT_PLAN_SCHEMA}, ['review', 'plan'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False

TOOLS += [base.tool('attribution_packet',
    'Recover the next 100 unreviewed material actor/actions after the final sheet plan and episode selection. '
    'Includes exact record-level attribution indices and referencing claim IDs, not automatic coverage judgments. '
    'Omit refs for the next pending batch; pass exact refs to revise saved coverage. Cache only.',
    {'refs': depth.array(depth_coverage.REF, 1, depth_coverage.BATCH_SIZE)}, []),
    base.tool('save_attribution_coverage',
    'Save or revise up to 100 actor/action coverage judgments for the exact review_version from attribution_packet. '
    'Each needs a claim carrying that exact role or a substantive omission reason. '
    'Changed evidence, prose, layout or episode selection invalidates these batches. '
    'Once every attribution is reviewed, depth_review may use an empty attribution_coverage list; full coverage is still required.',
    depth_coverage.SAVE_SCHEMA['properties'], depth_coverage.SAVE_SCHEMA['required'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False

TOOLS += [base.tool('extraction_packet',
    'Recover up to eight unreviewed sections from fully read cached originals. Extract each section before choosing stories. '
    'No source access or charge. Omit section_ids for the next unreviewed sections.',
    {'section_ids': retention.array(retention.TEXT, 1, 8)}, []),
    base.tool('save_extraction',
    'Save concrete events or specific context for each cached section. Preserve actor, action, date, state, significance '
    'and exact evidence. The host derives durable record notes only after all its sections are reviewed. '
    'Classify originals in source_kinds as work, discussion or evaluation; reuse the classification unless later substantive content corrects it. '
    'Empty originals need a context disposition with no spans or events. '
    'Header copies, repeated generic findings and participation placeholders are rejected.',
    retention.EXTRACTION_SCHEMA['properties'], retention.EXTRACTION_SCHEMA['required']),
    base.tool('episode_packet',
    'Recover extracted events in pages of 30 and a compact summary of the last episode selection. Cache only. '
    'Use these events to connect need, action, reaction, correction and later outcome before ranking stories.',
    {'offset': {'type': 'integer', 'minimum': 0}}, []),
    base.tool('episode_inventory',
    'Keep every extracted event in a selected or reserve episode, or give its specific exclusion. '
    'Choose stable episode IDs matching sheet accounts. Compare the strongest reserve with a selected account. '
    'After the first sheet plan, reconsider and resubmit this inventory before depth_review. '
    'For large archives, assignment_mode=saved combines current saved batches; supply episode definitions '
    'with empty event_ids and an empty excluded_events list. Every event is still required.',
    retention.INVENTORY_SCHEMA['properties'], retention.INVENTORY_SCHEMA['required'])]
TOOLS += [base.tool('episode_assignment_packet',
    'Recover the next 30 unassigned events, exact evidence pointers and current episode counts. '
    'Connect these to stable episodes; no automatic grouping or omission. Pass event_ids to revisit saved assignments. Cache only.',
    {'event_ids': retention.array(retention.TEXT, 1, retention.ASSIGNMENT_PACKET_SIZE)}, []),
    base.tool('save_episode_assignments',
    'Save or revise up to 100 explicit event-to-episode assignments, or evidence-specific exclusions, '
    'for the current retention_version. Changed extraction invalidates batches; changed assignments invalidate selection and depth review. '
    'After all events are assigned, finalize episode_inventory with assignment_mode=saved.',
    retention.ASSIGNMENT_SCHEMA['properties'], retention.ASSIGNMENT_SCHEMA['required'])]
for definition in TOOLS:
    if definition['name'] in {'save_extraction', 'episode_inventory', 'save_episode_assignments'}:
        definition['annotations']['readOnlyHint'] = False
TOOLS += [base.tool('resume_packet',
    'Recover the last saved draft, checked plan, depth audit and recent refusals after interruption. '
    'Cache only. Saved judgments are not automatically current; inspect research_status and repair stale gates.', {}, []),
    base.tool('turning_point_packet',
    'Review every retained event for responsibility changes, handoffs, stopped work, later use and changed approaches. '
    'Includes reserve/excluded origins and claim pointers. Omit event_ids for the next 50 unreviewed events.',
    {'event_ids': retention.array(retention.TEXT, 1, turning_points.BATCH_SIZE)}, []),
    base.tool('save_turning_points',
    'Save event-specific turning-point judgments against the current draft and selection. Connect consequential '
    'reserve events to selected accounts, preserve announced/planned states, and cite represented claims or explain omission. '
    'Review all events before depth_review and finish; these checks do not certify meaning.',
    turning_points.SAVE_SCHEMA['properties'], turning_points.SAVE_SCHEMA['required'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False
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
                                                'episode_packet', 'episode_inventory',
                                                'episode_assignment_packet', 'save_episode_assignments',
                                                'attribution_packet', 'save_attribution_coverage',
                                                'resume_packet', 'turning_point_packet', 'save_turning_points'}

    def __init__(self, corpus, scope, log, *, retention_required=True, export_protocol=None, turning_required=False):
        super().__init__(corpus, scope, log)
        self.retention_required = retention_required
        self.turning_required = turning_required
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
        if name == 'resume_packet':
            draft = next((e for e in reversed(self.events) if e['tool'] == 'draft_check'), None)
            plan = depth.latest_plan(self.events)
            audit = depth.latest_review(self.events)
            return {'draft': draft['arguments']['draft'] if draft else None,
                'draft_validation': draft['result'].get('errors', []) if draft else [],
                'checked_plan': plan['arguments'] if plan else None,
                'last_depth_audit': audit['arguments'] if audit else None,
                'recent_refusals': [{'tool': e['tool'], 'result': {k: e['result'][k] for k in
                    ('error', 'errors', 'valid', 'status', 'instruction') if k in e['result']}} for e in self.events[-10:]
                    if e['result'].get('error') or e['result'].get('valid') is False],
                'planning': self.planning(), 'cache_only': True}
        if name in {'turning_point_packet', 'save_turning_points'}:
            ctx = turning_points.context(self.events, list(self.full_reads().values()), spans)
            if name == 'turning_point_packet':
                return turning_points.packet(self.events, ctx, args.get('event_ids'))
            errors = turning_points.validate(args['decisions'], ctx)
            if args['review_version'] != ctx['version']:
                errors.append('Turning-point decisions belong to a stale draft, evidence or episode selection.')
            return {'valid': not errors, 'errors': errors, 'review_version': ctx['version'],
                    'semantic_checked': False, 'cache_only': True}
        if name in {'attribution_packet', 'save_attribution_coverage'}:
            version, review = self.coverage_context()
            notes = saved_notes(self.events)
            if name == 'attribution_packet':
                return depth_coverage.packet(self.events, notes, version, review, args.get('refs'))
            errors = depth_coverage.validate(args['attribution_coverage'], notes, review)
            if args['review_version'] != version:
                errors.append('Coverage belongs to a stale evidence, draft, plan or episode selection version.')
            return {'valid': not errors, 'errors': errors, 'review_version': version,
                    'semantic_checked': False, 'cache_only': True}
        if name in {'extraction_packet', 'save_extraction', 'episode_packet', 'episode_inventory',
                    'episode_assignment_packet', 'save_episode_assignments'}:
            records = list(self.full_reads().values())
            current = retention.state(records, self.events, spans)
            if name == 'episode_assignment_packet':
                return retention.assignment_packet(self.events, current, args.get('event_ids'))
            if name == 'save_episode_assignments':
                return retention.validate_assignments(args, current)
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
                        'inventory': {'hash': retention.inventory_hash(prior),
                            'episodes': [{k: v for k, v in episode.items() if k != 'event_ids'}
                                         for episode in prior['arguments']['episodes']],
                            'challenge': prior['arguments']['challenge']} if prior else None, 'cache_only': True}
            resolved, errors = retention.resolve_inventory(args, self.events, current)
            result = retention.validate_inventory(resolved, current)
            result['errors'] += errors
            result['valid'] = not result['errors']
            if args.get('assignment_mode') == 'saved':
                result['assignments_hash'] = retention.assignment_hash(self.events, current['version'])
            result['inventory_hash'] = retention.inventory_hash({'arguments': args, 'result': result})
            return result
        if name == 'depth_review':
            records = list(self.full_reads().values())
            evidence = evidence_version(records, self.events)
            plan = depth.latest_plan(self.events)
            if not plan or plan['result']['evidence_version'] != evidence:
                return depth.validate_review(args, self.events, records, saved_notes(self.events),
                                             self.scope, evidence, spans)
            version, _ = self.coverage_context()
            combined = dict(args, attribution_coverage=depth_coverage.combine(
                self.events, version, args['attribution_coverage']))
            result = depth.validate_review(combined, self.events, records, saved_notes(self.events), self.scope,
                                           evidence_version(records, self.events), spans)
            result.update(coverage_review_version=version,
                          coverage_batch_sequences=depth_coverage.contributing_sequences(self.events, version),
                          coverage_hash=depth_coverage.coverage_hash(self.events, version, args['attribution_coverage']))
            if self.retention_required:
                plan = depth.latest_plan(self.events)
                if plan:
                    result['errors'] += retention.plan_errors(plan['arguments']['plan'], records, self.events, spans, challenged=True)
                inventory = retention.latest_inventory(self.events, retention.state(records, self.events, spans))
                result['inventory_hash'] = retention.inventory_hash(inventory) if inventory else None
                result['valid'] = not result['errors']
            if self.turning_required:
                turning = turning_points.status(self.events, records, spans)
                result['errors'] += turning['errors']
                result['turning_points'] = turning
                result['valid'] = not result['errors']
            if not result['valid']:
                result['available_probe_receipts'] = self.probe_receipts()
            return result
        return super().local(name, args)

    def coverage_context(self):
        records = list(self.full_reads().values())
        inventory = retention.latest_inventory(self.events, retention.state(records, self.events, spans))
        inventory_hash = retention.inventory_hash(inventory) if inventory else None
        return depth_coverage.context(self.events, evidence_version(records, self.events), inventory_hash)

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
        if self.turning_required:
            result['turning_points'] = turning_points.status(self.events, list(self.full_reads().values()), spans)
        result['calls_remaining'] = self.source_budget - self.source_calls()
        result['earlier_start'] = self.scope.get('earlier_start', result['earlier_start'])
        if self.retention_required:
            current = retention.state(list(self.full_reads().values()), self.events, spans)
            result['writing']['recovery'] = ('extraction_packet, save_extraction and episode_packet recover cached '
                'evidence without a source charge, within the total request ceiling. save_notes is disabled.')
            result['retention'] = {'protocol': retention.PROTOCOL, 'sections': len(current['known']),
                'reviewed_sections': len(current['saved']), 'pending_sections': len(current['pending']),
                'events': len(current['events']), 'inventory_current': bool(retention.latest_inventory(self.events, current)),
                'next_step': 'Complete extraction; recover events through episode_packet or bounded episode_assignment_packet/save_episode_assignments, then finalize episode_inventory before drafting.'}
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
        if self.turning_required:
            turning = turning_points.status(self.events, list(self.full_reads().values()), spans)
            if not turning['current']:
                result['unresolved']['turning_points'] = turning['errors']
                result.update(allowed=False, status='review_turning_points', receipt_id=None)
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
    def __init__(self, corpus, scope, log, policy, *, retention_required=True, export_protocol=None, batch_writer=False, turning_required=False):
        self.corpus, self.scope, self.path, self.policy = corpus, scope, log, policy
        self.policy_path = log.parent / 'policy.json'
        self.policy_digest = digest(policy)
        self.batch_writer = batch_writer
        self.turning_required = turning_required
        self.records = {r['id']: r for r in corpus['records']}
        self.events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []
        self.retention_required = retention_required
        self.configure_export(export_protocol)

    def execute(self, name, args):
        if not self.batch_writer and (self.path.parent / 'extraction-batches/running.lock').exists():
            return {'error': 'extraction_in_progress', 'instruction': 'Wait for batch extraction to release this journal.'}
        # Revocation also blocks an already-running server and cache recovery.
        try:
            current = json.loads(self.policy_path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            return {'error': 'policy_unavailable', 'instruction': 'Stop research and restore or reconfigure the local policy.'}
        if digest(current) != self.policy_digest:
            return {'error': 'policy_changed', 'instruction': 'Stop research. Changed settings require a newly validated session.'}
        disk_events = [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines()] if self.path.exists() else []
        if disk_events != self.events:
            return {'error': 'journal_changed', 'instruction': 'Another writer changed this journal. Reconnect to load its saved progress.'}
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
    from research_lock import exclusive_run
    from research_sheet import outside_project
    workspace = outside_project(workspace)
    with exclusive_run(workspace / 'research-server.lock'):
        serve_locked(workspace)


def serve_locked(workspace):
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
    options = {'retention_required': required, 'export_protocol': session.get('export_protocol'),
               'turning_required': session.get('turning_point_protocol') == turning_points.PROTOCOL}
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
