"""Render portable career context with no dependencies or network access."""
import argparse
import base64
import copy
import hashlib
import html
import json
import os
import re
import tempfile
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
TEXT_FIELDS = ['title', 'period', 'summary', 'context', 'aim', 'contribution', 'sharedCredit', 'outcome']
LIST_FIELDS = ['decisions', 'limits', 'questions', 'sourceRefs']
KINDS = {'person_account', 'source_excerpt', 'redacted_excerpt', 'archive_summary', 'artifact_record'}
MIMES = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.webp': 'image/webp', '.gif': 'image/gif'}

def check_text(value, label, maximum=100_000):
    if not isinstance(value, str) or '\0' in value or len(value) > maximum:
        raise ValueError(f'{label} must be text of at most {maximum} characters, without NULs')

def keys(value, allowed, label):
    if not isinstance(value, dict) or set(value) - set(allowed):
        raise ValueError(f'{label} has an unsupported field or is not an object')

def validate(data):
    keys(data, ['schema', 'updatedAt', 'reviewStatus', 'person', 'accounts', 'sources', 'synthetic'], 'Sheet')
    if 'synthetic' in data and not isinstance(data['synthetic'], bool):
        raise ValueError('synthetic must be true or false')
    if data.get('schema') != 'career-context/v1' or data.get('reviewStatus') not in ['draft', 'person_reviewed']:
        raise ValueError('Unsupported schema or review status')
    date.fromisoformat(data['updatedAt'])
    person = data['person']; keys(person, ['name', 'overview', 'background'], 'Person')
    for field in ['name', 'overview']: check_text(person[field], field)
    if not isinstance(person.get('background', []), list): raise ValueError('Background must be a list')
    for line in person.get('background', []): check_text(line, 'Background item')
    for field, maximum in [('accounts', 80), ('sources', 160)]:
        if not isinstance(data[field], list) or len(data[field]) > maximum: raise ValueError(f'Invalid {field} collection')
        if any(not isinstance(item, dict) for item in data[field]):
            raise ValueError(f'{field} entries must be objects')
        ids = [item.get('id') for item in data[field]]
        if any(not isinstance(i, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}', i) for i in ids) or len(set(ids)) != len(ids):
            raise ValueError(f'{field} need unique safe IDs')
    source_ids = {s['id'] for s in data['sources']}; used = set(); artifact_ids = set()
    for source in data['sources']:
        keys(source, ['id', 'label', 'kind', 'content', 'scope', 'date', 'locator'], 'Source')
        if source['kind'] not in KINDS: raise ValueError('Invalid source kind')
        for field in ['label', 'content', 'scope']: check_text(source[field], field)
        for field in ['date', 'locator']:
            if field in source: check_text(source[field], field)
    for account in data['accounts']:
        keys(account, ['id', *TEXT_FIELDS, *LIST_FIELDS, 'artifacts'], 'Account')
        for field in TEXT_FIELDS: check_text(account[field], field)
        for field in LIST_FIELDS:
            if not isinstance(account[field], list): raise ValueError(f'{field} must be a list')
            for line in account[field]: check_text(line, field)
        if not account['sourceRefs'] or len(set(account['sourceRefs'])) != len(account['sourceRefs']) or set(account['sourceRefs']) - source_ids:
            raise ValueError('Each account needs unique references to included sources')
        used.update(account['sourceRefs'])
        if not isinstance(account.get('artifacts', []), list): raise ValueError('Artifacts must be a list')
        for artifact in account.get('artifacts', []):
            keys(artifact, ['id', 'title', 'caption', 'file', 'embeddedId', 'mediaType', 'sha256', '_dataUrl'], 'Artifact')
            for field in ['id', 'title', 'caption']: check_text(artifact[field], field)
            aid = artifact['id']
            if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}', aid) or aid in artifact_ids: raise ValueError('Artifacts need unique safe IDs')
            artifact_ids.add(aid)
    if used != source_ids: raise ValueError('Remove unreferenced source records from the packet')

class SheetReader(HTMLParser):
    def __init__(self): super().__init__(); self.capture = False; self.parts = []; self.images = {}
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'script' and attrs.get('id') == 'career-context-data': self.capture = True
        if tag == 'img' and attrs.get('id'): self.images[attrs['id']] = attrs.get('src', '')
    def handle_data(self, data):
        if self.capture: self.parts.append(data)
    def handle_endtag(self, tag):
        if tag == 'script': self.capture = False

def load_packet(source):
    return parse_packet(source.read_text(encoding='utf-8'), is_html=source.suffix.lower() in ['.html', '.htm'])


def parse_packet(raw, *, is_html=False):
    if len(raw.encode()) > 24 * 1024 * 1024: raise ValueError('Sheet exceeds 24 MiB')
    if not is_html: return json.loads(raw)
    parser = SheetReader(); parser.feed(raw); data = json.loads(''.join(parser.parts))
    for account in data['accounts']:
        for artifact in account.get('artifacts', []): artifact['_dataUrl'] = parser.images.get(artifact.get('embeddedId'), '')
    return data

def image_data(artifact, base):
    if 'file' in artifact:
        path = (base / artifact['file']).resolve(); mime = MIMES.get(path.suffix.lower()); raw = path.read_bytes()
    else:
        match = re.fullmatch(r'data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)', artifact.get('_dataUrl', ''))
        if not match: raise ValueError('The selected artifact has no embedded image or authoring file')
        mime = match[1]; raw = base64.b64decode(match[2], validate=True)
    if mime not in MIMES.values() or len(raw) > 2 * 1024 * 1024: raise ValueError('Image must be supported and at most 2 MiB')
    signatures = {'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'), 'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
                  'image/gif': raw.startswith((b'GIF87a', b'GIF89a')), 'image/webp': raw.startswith(b'RIFF') and raw[8:12] == b'WEBP'}
    if not signatures[mime]: raise ValueError('Image content does not match its declared format')
    return mime, raw

def render(source, destination, *, overwrite=True):
    data = load_packet(source); validate(data); packet = copy.deepcopy(data)
    esc = html.escape
    def paragraphs(text): return ''.join(f'<p>{esc(p)}</p>' for p in text.split('\n\n') if p.strip()) or '<p class="muted">Not recorded yet.</p>'
    def bullets(items): return '<ul>' + ''.join(f'<li>{esc(i)}</li>' for i in items) + '</ul>' if items else '<p class="muted">Not recorded yet.</p>'
    accounts = []
    for account in packet['accounts']:
        pictures = []
        for artifact in account.get('artifacts', []):
            mime, raw = image_data(artifact, source.parent); artifact.pop('file', None); artifact.pop('_dataUrl', None)
            artifact.update(embeddedId='artifact-'+artifact['id'], mediaType=mime, sha256=hashlib.sha256(raw).hexdigest())
            url = f'data:{mime};base64,' + base64.b64encode(raw).decode()
            pictures.append(f'<figure><img id="{artifact["embeddedId"]}" src="{url}" alt="{esc(artifact["title"])}" loading="lazy"><figcaption>{esc(artifact["caption"])}</figcaption></figure>')
        details = f'<div class="detail-grid"><div><h4>Context</h4>{paragraphs(account["context"])}<h4>What I wanted to change</h4>{paragraphs(account["aim"])}</div><div><h4>Decisions and approach</h4>{bullets(account["decisions"])}<h4>Shared work</h4>{paragraphs(account["sharedCredit"])}</div></div>'
        questions = '<h4>Still to clarify</h4>' + bullets(account['questions']) if account['questions'] else ''
        refs = ' · '.join(f'<a href="#source-{esc(ref)}">{esc(next(s["label"] for s in packet["sources"] if s["id"]==ref))}</a>' for ref in account['sourceRefs'])
        accounts.append(f'''<article class="account" id="account-{account['id']}"><div class="account-main"><div class="account-heading"><h3>{esc(account['title'])}</h3><span class="period">{esc(account['period']) or 'Period not recorded'}</span></div><div class="account-summary">{paragraphs(account['summary'])}</div><div class="facts"><div><h4>My contribution</h4>{paragraphs(account['contribution'])}</div><div><h4>What happened</h4>{paragraphs(account['outcome'])}</div></div><details class="context-details"><summary>Decisions, shared work and open points <span class="arrow" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m7 4 6 6-6 6"/></svg></span></summary>{details}<div class="limit"><h4>Limits of the account</h4>{bullets(account['limits'])}{questions}</div>{''.join(pictures)}<p class="references">Sources: {refs}</p></details></div></article>''')
    sources = []
    for s in packet['sources']:
        location = f'<p class="source-meta">{esc(s["locator"])}</p>' if s.get('locator') else ''
        source_date = f'<p class="source-meta">Source date: {esc(s["date"])}</p>' if s.get('date') else ''
        sources.append(f'<details class="source" id="source-{s["id"]}"><summary><span>{esc(s["label"])}</span><small>{esc(s["kind"].replace("_", " "))}</small><span class="arrow" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m7 4 6 6-6 6"/></svg></span></summary><div class="source-content">{source_date}{paragraphs(s["content"])}<p class="scope">{esc(s["scope"])}</p>{location}</div></details>')
    values = {
        'TITLE': esc(packet['person']['name'] + ' — Career context'), 'NAME': esc(packet['person']['name']),
        'OVERVIEW': paragraphs(packet['person']['overview']), 'BACKGROUND': bullets(packet['person'].get('background', [])),
        'DATE': esc(packet['updatedAt']), 'STATUS': 'Draft for review' if packet['reviewStatus']=='draft' else 'Reviewed by the person',
        'COUNT': f'{len(packet["accounts"])} work account' + ('' if len(packet['accounts']) == 1 else 's'),
        'DEMO': '<p class="demo-notice">Synthetic demo data. These work accounts are fictional.</p>' if packet.get('synthetic') else '',
        'ACCOUNTS': ''.join(accounts) or '<p class="empty">No work accounts recorded yet. Start with one project: what happened, what you did and what remains uncertain.</p>',
        'INDEX': ''.join(f'<a href="#account-{a["id"]}">{esc(a["title"])}</a>' for a in packet['accounts']),
        'SOURCES': ''.join(sources) or '<p>No sources included yet.</p>',
        'DATA': json.dumps(packet, ensure_ascii=True).replace('<', '\\u003c').replace('&', '\\u0026'),
    }
    template = (SKILL / 'assets/sheet.html').read_text(encoding='utf-8')
    output = re.sub(r'@@([A-Z]+)@@', lambda m: values[m[1]], template)
    if destination.is_symlink(): raise ValueError('Output must not be a symbolic link')
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix='.career-context-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(output.encode('utf-8'))
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)
    return {'path': str(destination), 'accounts': len(packet['accounts']), 'sources': len(packet['sources']), 'bytes': len(output.encode()), 'sha256': hashlib.sha256(output.encode()).hexdigest()}

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Selected context JSON or an existing HTML sheet")
    parser.add_argument("output", type=Path, help="HTML destination")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args(argv)
    try:
        source = args.input.expanduser().resolve()
        destination = args.output.expanduser().absolute()
        if destination.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("Choose an output ending in .html or .htm.")
        if destination.is_symlink():
            raise ValueError("Output must not be a symbolic link.")
        if destination.exists() and not args.force:
            raise ValueError("Output already exists; use --force to replace it.")
        if not destination.parent.is_dir():
            raise ValueError("Create the output folder first.")
        result = render(source, destination, overwrite=args.force)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Could not create the sheet: {error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
