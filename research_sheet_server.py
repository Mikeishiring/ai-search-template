"""Research-to-sheet MCP using fixed fictional sources and a durable local journal."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from research_sheet import (EXPERIMENTS, PLAN_SCHEMA, compile_sheet, digest,
                            draft_hash, evidence_version, load_session)
import autonomous_server as base
from mcp_server import check
from ownership_server import OwnershipSource, TOOLS as RESEARCH_TOOLS, DRAFT_SCHEMA
from completion_server import REQUEST_LIMIT

TOOLS = copy.deepcopy(RESEARCH_TOOLS) + [base.tool(
    'sheet_plan',
    'Validate and save the complete checked review plus its sheet layout. Field values select claim IDs; no second prose rewrite. '
    'Every claim must appear in an account. Use questions only for missing facts or personal meaning. Free local operation.',
    {'review': DRAFT_SCHEMA, 'plan': PLAN_SCHEMA}, ['review', 'plan'])]
TOOLS[-1]['annotations']['readOnlyHint'] = False


class SheetSource(OwnershipSource):
    def accessible(self, record):
        return (super().accessible(record) and record['source'] in self.scope['sources']
                and record.get('container') not in self.scope.get('excluded_containers', []))

    def dispatch(self, name, args):
        if 'source' in args and args['source'] not in self.scope['sources']:
            raise ValueError('Source outside selected scope')
        if name == 'read_attachment' and not any(
                self.accessible(r) and args['id'] in r.get('attachments', []) for r in self.records.values()):
            raise ValueError('Attachment outside selected scope')
        result = super().dispatch(name, args)
        if name == 'source_inventory':
            result['sources'] = [s for s in result['sources'] if s['id'] in self.scope['sources']]
        return result

    def planning(self):
        result = super().planning()
        outside = [r for r in result['unread_references'] if r['source'] not in self.scope['sources']]
        result['outside_scope_links'] = outside
        result['unread_references'] = [r for r in result['unread_references'] if r not in outside]
        plans = [e for e in self.events if e['tool'] == 'sheet_plan' and e['result'].get('valid')]
        version = evidence_version(list(self.full_reads().values()), self.events)
        result['writing']['sheet_plan_current'] = bool(plans and plans[-1]['result']['evidence_version'] == version)
        return result

    def finish(self):
        result = super().finish()
        if not self.planning()['writing']['sheet_plan_current']:
            result.update(allowed=False, status='plan_sheet', receipt_id=None)
        return result

    def execute(self, name, args):
        # A sealed journal can be rebuilt repeatedly, but cannot silently acquire new evidence.
        if self.events and self.events[-1]['tool'] == 'finish_check' and self.events[-1]['result'].get('allowed'):
            return {'error': 'session_sealed', 'instruction': 'Build the checked sheet from this saved journal.'}
        if name != 'sheet_plan':
            return super().execute(name, args)
        check(args, TOOLS[-1]['inputSchema'])
        if len(self.events) >= REQUEST_LIMIT:
            return {'error': 'request_limit_exhausted'}
        records = list(self.full_reads().values())
        _, validation = compile_sheet(args['review'], args['plan'], records, self.events,
                                      self.scope, self.corpus['snapshot'], draft=True, synthetic=self.corpus['synthetic'])
        current = evidence_version(records, self.events)
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
    def __init__(self, corpus, scope, log, policy):
        self.corpus, self.scope, self.path, self.policy = corpus, scope, log, policy
        self.policy_path = log.parent / 'policy.json'
        self.policy_digest = digest(policy)
        self.records = {r['id']: r for r in corpus['records']}
        self.events = [json.loads(line) for line in log.read_text(encoding='utf-8').splitlines()] if log.exists() else []

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
    server = LocalSheetSource(corpus, scope, log, policy) if local else SheetSource(corpus, scope, log)
    schemas = {(EXPERIMENTS / ('model/' + name + '.schema.json')).resolve()
               for name in ['ownership', 'retention', 'depth', 'completion', 'attribution', 'review']}
    if local:
        schemas.add((workspace / 'policy.json').resolve())
    base.TOOLS = copy.deepcopy(TOOLS)
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
