"""Review tracked/unignored release files; never copies personal workspaces."""
import argparse,hashlib,json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--write-manifest',action='store_true');args=parser.parse_args()
names=subprocess.check_output(['git','ls-files','--cached','--others','--exclude-standard','-z'],cwd=ROOT).decode().split('\0')
paths=sorted({name for name in names if name and name!='PUBLICATION-MANIFEST.json'})
patterns={
 'credential':r'(?:gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,}|xox[baprs]-[A-Za-z0-9-]{20,}|sk-(?:proj-|ant-)[A-Za-z0-9_-]{20,}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----)',
 'personal_path':r'(?i)(?:C:[\\/]Users[\\/]|/Users/|/home/)[A-Za-z0-9_-]+[\\/]',
 'email':r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',
 'live_source_link':r'https?://(?:[^/\s]+\.slack\.com/archives|app\.ashbyhq\.com/|(?:www\.)?notion\.so/|app\.notion\.[^/]+/)'
}
errors=[];files=[]
for name in paths:
    path=ROOT/name
    if not path.is_file() or path.is_symlink():errors.append((name,'missing file or symlink'));continue
    if name.startswith(('private/','sources/','derived/','analysis/','personal/')) or '.sqlite' in name:errors.append((name,'private/runtime path'))
    raw=path.read_bytes()
    if name == 'docs/career-context-preview.png':
        if not raw.startswith(b'\x89PNG\r\n\x1a\n') or len(raw) > 3 * 1024 * 1024:
            errors.append((name,'invalid or oversized reviewed preview'))
        files.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
        continue
    try:text=raw.decode('utf-8-sig')
    except UnicodeDecodeError:errors.append((name,'unreviewed binary'));continue
    for label,pattern in patterns.items():
        if re.search(pattern,text):errors.append((name,label))
    if name.endswith('.corpus.json'):
        corpus=json.loads(text)
        if corpus.get('synthetic') is not True:errors.append((name,'not labeled synthetic'))
    if name == 'examples/career-context.json' and json.loads(text).get('synthetic') is not True:
        errors.append((name,'public career example must be synthetic'))
    if name == 'CAREER-CONTEXT.html':
        payload=re.search(r'<script id="career-context-data" type="application/json">(.*?)</script>',text,re.S)
        if not payload or json.loads(payload[1]).get('synthetic') is not True:
            errors.append((name,'public sheet must be synthetic'))
    if name.endswith('.md'):
        for link in re.findall(r'\]\(([^)]+)\)',text):
            if re.match(r'^[A-Za-z]+:',link) or link.startswith('#'):continue
            target=link.split('#')[0].strip('<>')
            if target and not (path.parent/target).exists():errors.append((name,'missing local link: '+target))
    files.append({'path':name,'sha256':hashlib.sha256(raw).hexdigest()})
if errors:
    print(json.dumps({'blocked':errors},indent=2));raise SystemExit(1)
manifest={'synthetic_only':True,'method':'Reviewed code, docs and synthetic examples. File pattern scan is additional screening, not proof of anonymization or a universal secret detector. Personal workspaces are excluded.','files':files}
if args.write_manifest:(ROOT/'PUBLICATION-MANIFEST.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
else:
    old=json.loads((ROOT/'PUBLICATION-MANIFEST.json').read_text(encoding='utf-8'))
    assert {x['path']:x['sha256'] for x in old['files']}=={x['path']:x['sha256'] for x in files},'Manifest is stale; review changes before --write-manifest.'
print(json.dumps({'files':len(files),'patterns':'passed','relative_links':'passed','manifest':'written' if args.write_manifest else 'matched'}))
