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
    keys(data, ['schema', 'updatedAt', 'reviewStatus', 'person', 'accounts', 'sources', 'synthetic', 'profile', 'collection', 'presentation'], 'Sheet')
    if 'presentation' in data:
        presentation = data['presentation']
        keys(presentation, ['headline', 'files'], 'Presentation')
        check_text(presentation.get('headline', ''), 'Headline', 160)
        files = presentation.get('files', [])
        if not isinstance(files, list) or len(files) > 10: raise ValueError('Invalid related files')
        for item in files:
            keys(item, ['label', 'path'], 'Related file')
            check_text(item['label'], 'File label', 100)
            if not isinstance(item['path'], str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*\.(?:html|pdf|txt|json|sqlite)', item['path']):
                raise ValueError('Related files must be simple sibling filenames')
    if 'synthetic' in data and not isinstance(data['synthetic'], bool):
        raise ValueError('synthetic must be true or false')
    if data.get('schema') != 'career-context/v1' or data.get('reviewStatus') not in ['draft', 'person_reviewed']:
        raise ValueError('Unsupported schema or review status')
    date.fromisoformat(data['updatedAt'])
    person = data['person']; keys(person, ['name', 'overview', 'background'], 'Person')
    for field in ['name', 'overview']: check_text(person[field], field)
    if not isinstance(person.get('background', []), list): raise ValueError('Background must be a list')
    for line in person.get('background', []): check_text(line, 'Background item')
    if 'profile' in data:
        keys(data['profile'], ['disciplines', 'targetRoles', 'emphasis', 'referenceNotes'], 'Profile')
        for field in ['disciplines', 'targetRoles', 'emphasis']:
            items = data['profile'].get(field, [])
            if not isinstance(items, list) or len(items) > 20: raise ValueError(f'Invalid profile {field}')
            for item in items: check_text(item, field, 500)
        check_text(data['profile'].get('referenceNotes', ''), 'Reference notes', 3000)
    if not isinstance(data.get('collection', []), list) or len(data.get('collection', [])) > 80:
        raise ValueError('Invalid source collection inventory')
    for location in data.get('collection', []):
        keys(location, ['platform', 'location', 'access', 'status', 'scope', 'nextStep'], 'Collection location')
        for field in ['platform', 'location', 'scope', 'nextStep']: check_text(location[field], field, 3000)
        if location['access'] not in ['connector', 'export', 'supplied', 'unavailable']:
            raise ValueError('Invalid collection access')
        if location['status'] not in ['not_started', 'partial', 'read', 'blocked', 'excluded']:
            raise ValueError('Invalid collection status')
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
        keys(account, ['id', *TEXT_FIELDS, *LIST_FIELDS, 'artifacts', 'tags'], 'Account')
        if not isinstance(account.get('tags', []), list) or len(account.get('tags', [])) > 20: raise ValueError('Invalid account tags')
        for tag in account.get('tags', []): check_text(tag, 'Account tag', 200)
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
    if source.stat().st_size > 24 * 1024 * 1024: raise ValueError('Sheet exceeds 24 MiB')
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
        selected = Path(artifact['file'])
        path = (base / selected).resolve()
        if selected.is_absolute() or not path.is_relative_to(base.resolve()):
            raise ValueError('Select an image inside the input folder using a relative path')
        if path.stat().st_size > 2 * 1024 * 1024: raise ValueError('Image must be at most 2 MiB')
        mime = MIMES.get(path.suffix.lower()); raw = path.read_bytes()
    else:
        match = re.fullmatch(r'data:(image/(?:png|jpeg|webp|gif));base64,([A-Za-z0-9+/=]+)', artifact.get('_dataUrl', ''))
        if not match: raise ValueError('The selected artifact has no embedded image or authoring file')
        mime = match[1]; raw = base64.b64decode(match[2], validate=True)
    if mime not in MIMES.values() or len(raw) > 2 * 1024 * 1024: raise ValueError('Image must be supported and at most 2 MiB')
    signatures = {'image/png': raw.startswith(b'\x89PNG\r\n\x1a\n'), 'image/jpeg': raw.startswith(b'\xff\xd8\xff'),
                  'image/gif': raw.startswith((b'GIF87a', b'GIF89a')), 'image/webp': raw.startswith(b'RIFF') and raw[8:12] == b'WEBP'}
    if not signatures[mime]: raise ValueError('Image content does not match its declared format')
    if 'file' not in artifact and artifact.get('sha256') != hashlib.sha256(raw).hexdigest():
        raise ValueError('Embedded image does not match its saved checksum')
    return mime, raw


def publish_new(temporary, destination):
    # Windows rename is atomic and refuses an existing target. POSIX rename
    # replaces targets, so use an exclusive hard link there instead.
    if os.name == 'nt':
        os.rename(temporary, destination)
    else:
        os.link(temporary, destination)

def render(source, destination, *, overwrite=True):
    data = load_packet(source); validate(data); packet = copy.deepcopy(data)
    esc = html.escape
    def paragraphs(text): return ''.join(f'<p>{esc(p)}</p>' for p in text.split('\n\n') if p.strip())
    def bullets(items): return '<ul>' + ''.join(f'<li>{esc(i)}</li>' for i in items) + '</ul>' if items else ''
    accounts = []
    for account in packet['accounts']:
        pictures = []
        for artifact in account.get('artifacts', []):
            mime, raw = image_data(artifact, source.parent); artifact.pop('file', None); artifact.pop('_dataUrl', None)
            artifact.update(embeddedId='artifact-'+artifact['id'], mediaType=mime, sha256=hashlib.sha256(raw).hexdigest())
            url = f'data:{mime};base64,' + base64.b64encode(raw).decode()
            pictures.append(f'<figure><img id="{artifact["embeddedId"]}" src="{url}" alt="{esc(artifact["title"])}" loading="lazy"><figcaption>{esc(artifact["caption"])}</figcaption><button type="button" class="text-button artifact-expand" data-artifact="{artifact["embeddedId"]}" aria-haspopup="dialog">Enlarge image</button></figure>')
        fields = [('context', 'Context'), ('aim', 'Aim'), ('contribution', 'My contribution'), ('decisions', 'Decisions'), ('sharedCredit', 'Shared work'), ('outcome', 'Outcome')]
        details = '<div class="detail-grid">' + ''.join('<div><h4>' + label + '</h4>' + (bullets(account[key]) if isinstance(account[key], list) else paragraphs(account[key])) + '</div>' for key, label in fields if account[key]) + '</div>'
        questions = '<h4>Still to clarify</h4>' + bullets(account['questions']) if account['questions'] else ''
        refs = ' · '.join(f'<a href="#source-{esc(ref)}">{esc(next(s["label"] for s in packet["sources"] if s["id"]==ref))}</a>' for ref in account['sourceRefs'])
        limits = '<div class="limit" aria-label="Limits">' + bullets(account['limits']) + '</div>' if account['limits'] else ''
        accounts.append(f'''<article class="account" id="account-{account['id']}"><div class="account-main"><div class="account-heading"><h3>{esc(account['title'])}</h3><span class="period">{esc(account['period']) or 'Period not recorded'}</span></div><div class="account-summary">{paragraphs(account['summary'])}</div>{''.join(pictures)}{limits}<details class="context-details"><summary>Context &amp; evidence <span class="arrow" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m7 4 6 6-6 6"/></svg></span></summary>{details}{questions}<p class="references">Sources: {refs}</p></details></div></article>''')
    sources = []
    for s in packet['sources']:
        location = f'<p class="source-meta">{esc(s["locator"])}</p>' if s.get('locator') else ''
        source_date = f'<p class="source-meta">Source date: {esc(s["date"])}</p>' if s.get('date') else ''
        sources.append(f'<details class="source" id="source-{s["id"]}"><summary><span>{esc(s["label"])}</span><small>{esc(s["kind"].replace("_", " "))}</small><span class="arrow" aria-hidden="true"><svg viewBox="0 0 20 20"><path d="m7 4 6 6-6 6"/></svg></span></summary><div class="source-content">{source_date}{paragraphs(s["content"])}<p class="scope">{esc(s["scope"])}</p>{location}</div></details>')
    profile = packet.get('profile', {})
    profile_html = ''.join('<div><dt>' + label + '</dt><dd>' + esc(' · '.join(profile[field])) + '</dd></div>'
                           for field, label in [('disciplines', 'Work'), ('targetRoles', 'Exploring'), ('emphasis', 'Focus')] if profile.get(field))
    coverage = ''.join('<tr>' + ''.join('<td>' + esc(location[field].replace('_', ' ') if field == 'status' else location[field]) + '</td>'
                                      for field in ['platform', 'location', 'status', 'scope', 'nextStep']) + '</tr>' for location in packet.get('collection', []))
    values = {
        'HEADLINE': esc(packet.get('presentation', {}).get('headline') or 'Career context.'),
        'FILES': '<nav class="related-files" aria-label="Local files">' + ''.join(f'<a href="{esc(item["path"])}">{esc(item["label"])}</a>' for item in packet.get('presentation', {}).get('files', [])) + '</nav>',
        'OPTIONS': ''.join(f'<option value="{a["id"]}">{esc(a["title"])}</option>' for a in packet['accounts']),
        'PROFILE': '<dl class="profile">' + profile_html + '</dl>' if profile_html else '',
        'COVERAGE': '<details class="coverage"><summary>Source coverage</summary><div class="table-scroll"><table><thead><tr><th>Platform</th><th>Location</th><th>State</th><th>Read scope</th><th>Next step</th></tr></thead><tbody>' + coverage + '</tbody></table></div></details>' if coverage else '',
        'TITLE': esc(packet['person']['name'] + ' — Career context'), 'NAME': esc(packet['person']['name']),
        'OVERVIEW': paragraphs(packet['person']['overview']), 'BACKGROUND': ('<section class="background" aria-labelledby="background-title"><h2 id="background-title">Broader background</h2>' + bullets(packet['person']['background']) + '</section>') if packet['person'].get('background') else '',
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
    if len(output.encode('utf-8')) > 24 * 1024 * 1024:
        raise ValueError('Rendered sheet exceeds 24 MiB; select fewer or smaller images')
    if destination.is_symlink(): raise ValueError('Output must not be a symbolic link')
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix='.career-context-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream: stream.write(output.encode('utf-8'))
        if overwrite:
            os.replace(temporary, destination)
        else:
            publish_new(temporary, destination)
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
