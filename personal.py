"""Local-only personal evidence workspace. No network, model calls or Git operations."""
import argparse, hashlib, html, json, os, tempfile
from datetime import date
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
STATES = ('offered', 'requested', 'planned', 'in_progress', 'completed', 'reported', 'unknown')
MAX_INPUT = 20 * 1024 * 1024

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()

def save(path, value):
    text = json.dumps(value, indent=2, ensure_ascii=False) if not isinstance(value, str) else value
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.writing-')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream: stream.write(text)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp): os.unlink(temp)

def location(path):
    root = Path(path).expanduser().resolve()
    if root.is_relative_to(PROJECT):
        raise ValueError('Choose a workspace outside the template checkout. Private inputs must not enter this repository.')
    return root

def read_json(path):
    if path.stat().st_size > MAX_INPUT: raise ValueError('JSON exceeds the 20 MiB MVP limit; split it into smaller imports.')
    return json.loads(path.read_text(encoding='utf-8-sig'))

def load(path):
    root = location(path)
    for name in ['workspace.json', 'records.json', 'claims.json']:
        if (root/name).is_symlink(): raise ValueError('Workspace files must not be symbolic links.')
    config = read_json(root/'workspace.json')
    if config.get('format') != 'personal-evidence-v1': raise ValueError('Not a personal evidence workspace. Run init first.')
    return root, config, read_json(root/'records.json'), read_json(root/'claims.json')

def init(path, title, synthetic=False):
    root = location(path)
    if root.exists(): raise ValueError('Destination already exists; choose a new folder. Nothing was overwritten.')
    if not title.strip(): raise ValueError('Workspace title cannot be empty.')
    root.mkdir(parents=True)
    save(root/'workspace.json', {'format':'personal-evidence-v1', 'title':title, 'synthetic':synthetic, 'source_coverage':'User-selected imports only; archive completeness is unknown.'})
    save(root/'records.json', {'versions':{}, 'latest':{}})
    save(root/'claims.json', [])
    save(root/'.gitignore', '.env\n.env.*\n*.pem\n*.key\ncredentials*\n.writing-*\n')
    save(root/'README.md', '# Private evidence workspace\n\nThis folder is local-only until you upload or sync it. The dashboard contains source text and is private too. No model or source account is connected. If you choose GitHub backup, create an empty private repository and verify its visibility before pushing. Keep this folder outside the public template.\n')
    return {'workspace':str(root), 'network_used':False, 'next':'Import selected records, then build.'}

def validate_record(raw):
    required = {'id', 'source', 'title', 'date', 'author', 'text'}
    if not isinstance(raw, dict) or not required <= raw.keys() or set(raw)-required-{'parent_id','url'}:
        raise ValueError('Each record needs id, source, title, date, author and text; only parent_id and url are optional.')
    if any(not isinstance(raw[k], str) or not raw[k].strip() for k in required): raise ValueError('Required record fields must be nonempty strings.')
    if date.fromisoformat(raw['date']).isoformat() != raw['date']: raise ValueError('Dates must use YYYY-MM-DD.')
    for key in ['parent_id','url']:
        if key in raw and not isinstance(raw[key], str): raise ValueError('Optional fields must be strings.')
    if raw.get('url') and not raw['url'].startswith(('https://','http://')): raise ValueError('Source URL must be HTTP(S) or omitted.')
    return dict(raw)

def import_records(path, items):
    root, config, records, claims = load(path)
    if not isinstance(items, list) or not items: raise ValueError('Import JSON must be a nonempty array of normalized records, not a raw service export.')
    validated = [validate_record(item) for item in items]  # Validate entire batch before writing.
    keys = [json.dumps([r['source'],r['id']]) for r in validated]
    if len(set(keys)) != len(keys): raise ValueError('One import may contain only one version per source/id.')
    added = unchanged = 0
    for raw, key in zip(validated, keys):
        revision = digest(raw)
        if revision in records['versions']:
            unchanged += 1
            # Re-importing an older capture must not roll the latest revision back.
            continue
        records['versions'][revision] = raw
        records['latest'][key] = revision
        added += 1
    if len(json.dumps(records).encode()) > MAX_INPUT: raise ValueError('Workspace exceeds the 20 MiB MVP limit; use a smaller research scope.')
    save(root/'records.json', records)
    return {'new_versions':added, 'unchanged':unchanged, 'current_records':len(records['latest']), 'network_used':False}

def add_claim(path, source, record_id, statement, actor, state, quote, limits, start=None):
    root, config, records, claims = load(path)
    if state not in STATES: raise ValueError('Unknown action state.')
    if not all(v.strip() for v in [statement, actor, quote, limits]): raise ValueError('Statement, actor, quotation and limits must be nonempty.')
    revision = records['latest'].get(json.dumps([source,record_id]))
    if not revision: raise ValueError('No matching imported source/id.')
    text = records['versions'][revision]['text']
    if start is None:
        start = text.find(quote)
        if start < 0 or text.find(quote,start+1) >= 0: raise ValueError('Quote must occur exactly once, or provide its zero-based --start offset.')
    if start < 0 or text[start:start+len(quote)] != quote: raise ValueError('Quote does not match the selected source span.')
    claim = {'statement':statement, 'actor':actor, 'state':state, 'limits':limits, 'record_hash':revision, 'start':start, 'end':start+len(quote), 'quote':quote, 'review_status':'needs_review'}
    claim['id'] = digest(claim)[:16]
    if not any(c['id']==claim['id'] for c in claims): claims.append(claim)
    if len(json.dumps(claims).encode()) > MAX_INPUT: raise ValueError('Claim store exceeds the 20 MiB MVP limit; use a smaller research scope.')
    save(root/'claims.json', claims)
    return {'claim_id':claim['id'], 'status':'needs_review', 'exact_quote_checked':True, 'meaning_checked':False}

def claim_status(claim, records):
    record = records['versions'].get(claim.get('record_hash'))
    if not record or digest(record)!=claim['record_hash']: raise ValueError('Claim refers to missing or altered source content.')
    if record['text'][claim['start']:claim['end']] != claim['quote']: raise ValueError('Claim quotation was altered; repair the claim before building.')
    return records['latest'].get(json.dumps([record['source'],record['id']])) != claim['record_hash']

def build(path):
    root, config, records, claims = load(path)
    for revision, record in records['versions'].items():
        validate_record(record)
        if digest(record)!=revision: raise ValueError('An archived source version changed; do not edit records.json by hand.')
    if any(v not in records['versions'] for v in records['latest'].values()): raise ValueError('Current source pointer is missing.')
    stale = {c['id']:claim_status(c,records) for c in claims}
    esc = lambda value: html.escape(str(value), quote=True)
    rows=[]
    for c in claims:
        r=records['versions'][c['record_hash']]
        rows.append(f'<article><p class="meta">{esc(c["actor"])} · {esc(c["state"])} · '+('Source changed — re-review required' if stale[c['id']] else 'Needs review')+f'</p><h3>{esc(c["statement"])}</h3><p>{esc(c["limits"])}</p><blockquote>{esc(c["quote"])}</blockquote><a href="#source-{c["record_hash"]}">{esc(r["source"])} / {esc(r["id"])} · {esc(r["date"])}</a></article>')
    evidence=[]
    for revision,r in sorted(records['versions'].items(),key=lambda item:(item[1]['date'],item[1]['source'],item[1]['id'])):
        current=revision in records['latest'].values()
        link=f'<p><a href="{esc(r["url"])}" rel="noreferrer noopener">Open original source online</a> · opening this link contacts that service</p>' if r.get('url') else ''
        evidence.append(f'<details id="source-{revision}"><summary>{esc(r["date"])} · {esc(r["title"])} · '+('current capture' if current else 'earlier capture')+f'</summary><p class="meta">{esc(r["source"])} / {esc(r["id"])} · {esc(r["author"])}</p><p>Parent: {esc(r.get("parent_id") or "not supplied")}</p><pre>{esc(r["text"])}</pre>{link}</details>')
    body=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"><title>{esc(config['title'])}</title><style>
    :root{{color-scheme:light}}*{{box-sizing:border-box}}body{{margin:0;background:#fbfcf7;color:#182923;font:17px/1.6 system-ui,sans-serif}}h1,h3,summary,a{{overflow-wrap:anywhere}}main{{max-width:920px;margin:auto;padding:48px 24px}}h1{{font-size:clamp(32px,6vw,52px);line-height:1.1;letter-spacing:-.04em}}h2{{font-size:25px}}h3{{font-size:20px;font-weight:550}}a{{color:#0f6e67}}.meta{{color:#53665e;font-size:14px}}.counts{{display:flex;gap:30px;flex-wrap:wrap;border-block:1px solid #cbd7ce;padding:18px 0}}.counts strong{{display:block;font-size:30px}}section{{padding:24px 0}}article,details{{padding:20px 0;border-top:1px solid #cbd7ce}}blockquote{{margin:16px 0;padding-left:18px;border-left:3px solid #0f6e67}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font:inherit}}summary{{cursor:pointer;min-height:44px}}details:target{{background:#e9f0ea}}a:focus-visible,summary:focus-visible{{outline:3px solid #0f6e67;outline-offset:4px}}@media(max-width:600px){{main{{padding:28px 18px}}.counts{{gap:18px}}}}@media(prefers-reduced-motion:reduce){{*{{scroll-behavior:auto}}}}
    </style><main>{"<p class=meta>Synthetic demo data</p>" if config.get("synthetic") else ""}<p class="meta">Private local report · includes source text</p><h1>{esc(config['title'])}</h1><p>{esc(config['source_coverage'])}</p><nav><a href="#claims">Claims</a> · <a href="#sources">Sources</a></nav><div class="counts"><div><strong>{len(records['latest'])}</strong>imported records</div><div><strong>{len(claims)}</strong>proposed claims</div><div><strong>{sum(stale.values())}</strong>claims with newer sources</div></div><p class="meta">Counts come from this workspace’s records.json and claims.json. They do not measure source-system coverage or establish claim accuracy.</p><section id="claims"><h2>Claims and limits</h2>{''.join(rows) or '<p>No claims yet. Use add-claim with an exact quotation and an explicit limit.</p>'}<p class="meta">Exact quotations are checked. Meaning, attribution and delivery claims still need human review. No AI inference runs when this page opens.</p></section><section id="sources"><h2>Source captures</h2>{''.join(evidence) or '<p>No sources imported. Import a normalized JSON file or a selected UTF-8 text document.</p>'}</section><p class="meta">This HTML embeds private evidence. Keep it in your private workspace; do not publish it through the public template or Pages. No external assets or background requests are included.</p></main></html>'''
    target=root/'DASHBOARD.html'
    if target.is_symlink(): raise ValueError('Dashboard output must not be a symbolic link.')
    save(target,body)
    return {'dashboard':str(target), 'records':len(records['latest']), 'claims':len(claims), 'stale_claims':sum(stale.values()), 'network_used':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__);commands=parser.add_subparsers(dest='command',required=True)
    p=commands.add_parser('init');p.add_argument('workspace');p.add_argument('--title',required=True);p.add_argument('--synthetic',action='store_true',help='Label a fictional practice workspace; not an anonymization check')
    p=commands.add_parser('import-json');p.add_argument('workspace');p.add_argument('file')
    p=commands.add_parser('import-text');p.add_argument('workspace');p.add_argument('file')
    for name in ['source','id','title','date','author']:p.add_argument('--'+name,required=True)
    p.add_argument('--url',default='');p.add_argument('--parent-id',default='')
    p=commands.add_parser('add-claim');p.add_argument('workspace')
    for name in ['source','id','statement','actor','quote','limits']:p.add_argument('--'+name,required=True)
    p.add_argument('--state',choices=STATES,required=True);p.add_argument('--start',type=int)
    p=commands.add_parser('build');p.add_argument('workspace')
    args=parser.parse_args()
    try:
        if args.command=='init':result=init(args.workspace,args.title,args.synthetic)
        elif args.command=='build':result=build(args.workspace)
        elif args.command=='import-json':result=import_records(args.workspace,read_json(Path(args.file)))
        elif args.command=='import-text':
            file=Path(args.file)
            if file.suffix.lower() not in {'.txt','.md'} or file.stat().st_size>MAX_INPUT:raise ValueError('Use a UTF-8 .txt or .md file up to 20 MiB. PDF, ZIP and CSV extraction is not implemented.')
            result=import_records(args.workspace,[{'id':args.id,'source':args.source,'title':args.title,'date':args.date,'author':args.author,'text':file.read_text(encoding='utf-8-sig'),'url':args.url,'parent_id':args.parent_id}])
        else:result=add_claim(args.workspace,args.source,args.id,args.statement,args.actor,args.state,args.quote,args.limits,args.start)
        print(json.dumps(result,ensure_ascii=True))
    except (ValueError,KeyError,OSError,TypeError) as error:parser.exit(2, str(error)+'\n')

if __name__=='__main__':main()
