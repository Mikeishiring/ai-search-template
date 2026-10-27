"""Render an evidence-linked resume draft from current context and a model's projection."""
import argparse
import copy
from datetime import date
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

_spec = importlib.util.spec_from_file_location('interview_helpers', Path(__file__).with_name('render_interview.py'))
helpers = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(helpers)


def prepare(context, draft, fingerprint):
    helpers.shape(draft, ['schema', 'contextSha256', 'preparedOn', 'target', 'referenceNotes', 'summary', 'sections'],
                  'Resume', optional=['contact'])
    if draft['schema'] != 'resume-draft/v1':
        raise ValueError('Unsupported resume schema')
    if draft['contextSha256'] != fingerprint:
        raise ValueError('Career context changed. Read it and regenerate the resume.')
    date.fromisoformat(draft['preparedOn'])
    if draft['target'] is not None:
        helpers.text(draft['target'], 'Target')
    helpers.render_context.check_text(draft['referenceNotes'], 'Reference notes', 3000)
    accounts = {a['id']: a for a in context['accounts']}
    used = set()

    def references(ids):
        helpers.collection(ids, 'Account references')
        if any(not isinstance(key, str) or key not in accounts for key in ids) or len(set(ids)) != len(ids):
            raise ValueError('Resume entries must reference unique existing account IDs')
        used.update(ids)

    def statement(item):
        helpers.shape(item, ['text', 'accountIds'], 'Supported statement')
        helpers.text(item['text'], 'Statement')
        references(item['accountIds'])

    if draft['summary'] is not None:
        statement(draft['summary'])
    helpers.collection(draft.get('contact', []), 'Contact lines', minimum=0, maximum=6)
    for item in draft.get('contact', []):
        statement(item)
    helpers.collection(draft['sections'], 'Resume sections', maximum=12)
    for section in draft['sections']:
        helpers.shape(section, ['title', 'entries'], 'Resume section')
        helpers.text(section['title'], 'Section title')
        helpers.collection(section['entries'], 'Section entries', maximum=20)
        for entry in section['entries']:
            helpers.shape(entry, ['heading', 'details', 'bullets', 'accountIds'], 'Resume entry')
            helpers.text(entry['heading'], 'Entry heading')
            helpers.render_context.check_text(entry['details'], 'Entry details', 3000)
            helpers.collection(entry['bullets'], 'Resume bullets', minimum=0, maximum=8)
            for bullet in entry['bullets']:
                helpers.text(bullet, 'Resume bullet')
            references(entry['accountIds'])
    selected = [copy.deepcopy(a) for a in context['accounts'] if a['id'] in used]
    source_ids = {key for a in selected for key in a['sourceRefs']}
    for account in selected:
        # No hidden file reads or image copies in the resume projection.
        account.pop('artifacts', None)
    return {**copy.deepcopy(draft), 'person': context['person']['name'], 'reviewStatus': 'draft',
            'synthetic': context.get('synthetic', False), 'accounts': selected,
            'sources': [copy.deepcopy(s) for s in context['sources'] if s['id'] in source_ids]}


def resume_text(packet):
    lines = [packet['person'], 'Draft for review']
    if packet['synthetic']:
        lines.append('Synthetic demo data')
    if packet['target']:
        lines.append(packet['target'])
    lines.extend(item['text'] for item in packet.get('contact', []))
    if packet['summary']:
        lines.extend(['', packet['summary']['text']])
    for section in packet['sections']:
        lines.extend(['', section['title']])
        for entry in section['entries']:
            lines.extend(['', entry['heading']])
            if entry['details']:
                lines.append(entry['details'])
            lines.extend('- ' + text for text in entry['bullets'])
    return '\n'.join(lines) + '\n'


def render_html(packet):
    esc = helpers.escaped
    sections = []
    for section in packet['sections']:
        entries = []
        for entry in section['entries']:
            refs = ' · '.join(f'<a href="#account-{esc(key)}">{esc(next(a["title"] for a in packet["accounts"] if a["id"] == key))}</a>' for key in entry['accountIds'])
            entries.append(f'<article><h3>{esc(entry["heading"])}</h3>' +
                           (f'<p class="meta">{esc(entry["details"])}</p>' if entry['details'] else '') +
                           helpers.bullets(entry['bullets']) + f'<div class="entry-sources">Evidence: {refs}</div></article>')
        sections.append(f'<section><h2>{esc(section["title"])}</h2>{"".join(entries)}</section>')
    evidence = []
    for account in packet['accounts']:
        story = {'id': account['id'], 'account': account,
                 'evidence': [s for s in packet['sources'] if s['id'] in account['sourceRefs']]}
        evidence.append(f'<section id="account-{esc(account["id"])}"><h3>{esc(account["title"])}</h3>' + helpers.source_details(story) + '</section>')
    values = {
        'NAME': esc(packet['person']), 'TITLE': esc(packet['person'] + ' — Resume draft'),
        'TARGET': '<p class="target">' + esc(packet['target']) + '</p>' if packet['target'] else '',
        'CONTACT': ''.join('<p>' + esc(item['text']) + '</p>' for item in packet.get('contact', [])),
        'SUMMARY': '<div class="summary">' + helpers.paragraphs(packet['summary']['text']) + '</div>' if packet['summary'] else '',
        'SECTIONS': ''.join(sections), 'EVIDENCE': ''.join(evidence),
        'REFERENCE': helpers.paragraphs(packet['referenceNotes']) if packet['referenceNotes'] else '',
        'DEMO': '<span>Synthetic demo data</span>' if packet['synthetic'] else '',
        'TEXT': esc(resume_text(packet)),
        'DATA': json.dumps(packet, ensure_ascii=True).replace('<', '\\u003c').replace('&', '\\u0026'),
    }
    template = (helpers.render_context.SKILL / 'assets/resume.html').read_text(encoding='utf-8')
    return re.sub(r'@@([A-Z]+)@@', lambda match: values[match[1]], template)


def render(source, projection, destination, *, overwrite=False):
    inspected = helpers.inspect_context(source)
    if projection.stat().st_size > 4 * 1024 * 1024:
        raise ValueError('Resume projection exceeds 4 MiB')
    draft = json.loads(projection.read_text(encoding='utf-8'))
    packet = prepare(inspected['context'], draft, inspected['contextSha256'])
    raw = render_html(packet).encode('utf-8')
    if destination.is_symlink() or destination.resolve() in {source.resolve(), projection.resolve()}:
        raise ValueError('Use a separate output; source files are preserved')
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix='.resume-', suffix='.tmp')
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
        if overwrite:
            os.replace(temporary, destination)
        else:
            helpers.render_context.publish_new(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {'path': str(destination), 'accounts': len(packet['accounts']), 'sha256': hashlib.sha256(raw).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=Path)
    parser.add_argument('projection', nargs='?', type=Path)
    parser.add_argument('output', nargs='?', type=Path)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args(argv)
    try:
        source = args.input.expanduser().resolve()
        if args.inspect:
            if args.projection or args.output or args.force:
                raise ValueError('--inspect accepts only the context input')
            result = helpers.inspect_context(source)
        else:
            if not args.projection or not args.output:
                raise ValueError('Supply a resume projection and an HTML destination')
            output = args.output.expanduser().absolute()
            if output.suffix.lower() not in {'.html', '.htm'} or output.resolve().is_relative_to(helpers.render_context.SKILL):
                raise ValueError('Choose a private HTML output outside the skill')
            result = render(source, args.projection.expanduser().resolve(), output, overwrite=args.force)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f'Could not create the resume: {error}\n')
    print(json.dumps(result, ensure_ascii=True))


if __name__ == '__main__':
    main()
