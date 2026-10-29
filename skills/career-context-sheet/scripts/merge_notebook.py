"""Reconcile a saved notebook into one career-context packet, without losing evidence."""
import argparse
import base64
import copy
import hashlib
import importlib.util
import json
from html.parser import HTMLParser
from pathlib import Path

spec = importlib.util.spec_from_file_location('career_context', Path(__file__).with_name('render_context.py'))
renderer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(renderer)


class NotebookReader(HTMLParser):
    def __init__(self):
        super().__init__(); self.capture = False; self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag == 'script' and dict(attrs).get('id') == 'career-draft-data': self.capture = True

    def handle_data(self, data):
        if self.capture: self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == 'script': self.capture = False


def merge(packet, draft):
    renderer.validate(packet)
    legacy = renderer.load_helper('render_notebook')
    legacy.validate_overlay(draft)
    packet = copy.deepcopy(packet)
    original = {a['id']: a for a in draft['accounts']}
    accounts = {a['id']: a for a in packet['accounts']}
    sources = {s['id']: s for s in packet['sources']}

    def retain_source(title, content, date='', locator='', kind='archive_summary', scope='Saved notebook material, retained unchanged. No fresh source verification.'):
        record = dict(label=title, content=content, date=date, locator=locator, kind=kind, scope=scope)
        identity = hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:24]
        key = 'notebook-' + identity
        if key not in sources:
            record['id'] = key; sources[key] = record; packet['sources'].append(record)
        return key

    def source_refs(item):
        refs = []
        for source in item.get('sources', []):
            refs.append(retain_source(source.get('title', 'Saved notebook source'), source.get('text', ''),
                                      source.get('date', ''), source.get('url', ''),
                                      scope='Saved notebook source; original classification: ' + source.get('kind', 'record') + '. Selected text retained unchanged, not a fresh read of the original.'))
        return list(dict.fromkeys(refs))

    def snapshot(item, label):
        retained = {k: v for k, v in item.items() if k not in ['sources', 'image', 'images']}
        return retain_source(label, json.dumps(retained, ensure_ascii=False, indent=2))

    for old in draft['accounts']:
        key = old['id']
        refs = source_refs(old) + [snapshot(old, 'Saved notebook account: ' + old['title'])]
        if key not in accounts:
            account = dict(id=key, title=old['title'], period=old.get('period', ''), summary=old.get('problem', ''),
                           context=old.get('context', ''), aim=old.get('reason', ''), contribution=old.get('action', ''),
                           sharedCredit=old.get('shared', ''), outcome=old.get('after', ''),
                           decisions=[old[f] for f in ['responsibility', 'choice', 'alternative', 'cost'] if old.get(f)],
                           limits=[old['limit']] if old.get('limit') else [],
                           questions=old.get('openQuestions', '').splitlines(), sourceRefs=[])
            packet['accounts'].append(account); accounts[key] = account
        account = accounts[key]
        account['sourceRefs'] = list(dict.fromkeys(account['sourceRefs'] + refs))
        images = ([old['image']] if old.get('image') else []) + old.get('images', [])
        for i, image in enumerate(images):
            if not image.get('data', '').startswith('data:image/'): continue
            raw = base64.b64decode(image['data'].split(',', 1)[1], validate=True)
            aid = 'notebook-' + key + '-' + str(i + 1)
            if not any(a['id'] == aid for a in account.get('artifacts', [])):
                account.setdefault('artifacts', []).append(dict(id=aid, title=image.get('alt') or old['title'],
                    caption=image.get('caption', ''), embeddedId='artifact-' + aid,
                    mediaType=image['data'].split(';')[0][5:], sha256=hashlib.sha256(raw).hexdigest(), _dataUrl=image['data']))
    if not original: raise ValueError('Notebook has no work accounts to reconcile')
    profile_ref = snapshot({'profile': draft['profile'], 'directions': draft.get('directions', []),
                            'shareIntro': draft.get('shareIntro', False)}, 'Saved notebook profile and directions')
    first = accounts[next(iter(original))]
    first['sourceRefs'] = list(dict.fromkeys(first['sourceRefs'] + [profile_ref]))
    timeline = {p['id']: p for p in packet.get('timeline', [])}
    for old in draft.get('quarters', []):
        linked = old.get('accountId', '')
        if linked and linked not in accounts: raise ValueError('Notebook period references a missing work account')
        period = dict(id=old['id'], period=old['period'], title=old['title'], focus=old.get('focus', ''),
                      actions=old.get('actions', []), tension=old.get('tension', ''), approach=old.get('style', ''),
                      questions=old.get('questions', '').splitlines(),
                      sourceRefs=source_refs(old) + [snapshot(old, 'Saved career period: ' + old['period'])],
                      accountIds=[linked] if linked else [])
        if period['id'] in timeline and timeline[period['id']] != period:
            raise ValueError('Both inputs contain different versions of timeline period ' + period['id'] + '; reconcile before merging')
        timeline[period['id']] = period
    packet['timeline'] = list(timeline.values())
    # Existing preparation is never silently replaced by an older saved notebook.
    if 'interview' in packet:
        raise ValueError('Context already has interview preparation; reconcile its stories explicitly before importing another notebook')
    stories, questions = [], []
    labels = [('problem', 'Situation'), ('responsibility', 'My responsibility'), ('choice', 'Decision'),
              ('alternative', 'Alternative'), ('cost', 'Trade-off'), ('reason', 'Why'), ('action', 'My part'),
              ('after', 'What happened'), ('shared', 'Shared work'), ('limit', 'Limits')]
    for old in draft['accounts']:
        chapters = [{'title': label, 'text': old[field]} for field, label in labels if old.get(field)]
        if not chapters: raise ValueError('Notebook story needs substantive material')
        answer = '\n\n'.join(old[f] for f in ['problem', 'choice', 'action', 'after', 'shared', 'limit'] if old.get(f))
        stories.append(dict(id=old['id'], tests='Explain your contribution, the decision and what the evidence supports.',
                            takeaway=old.get('reason') or old.get('problem') or old['title'], chapters=chapters,
                            timeline=[{'when': old.get('period') or 'Dates not recorded', 'text': old.get('after') or old.get('action') or old['title']}],
                            practice=old.get('practice', '')))
        questions.append(dict(id='discuss-' + old['id'], question='Talk me through ' + old['title'].rstrip('.') + '.',
                              tests='Your contribution, judgment and the limits of the outcome.', storyId=old['id'],
                              reason='This is the saved work account, with its shared credit and limitations.', answer=answer))
    leads = sorted(draft['accounts'], key=lambda a: len(a.get('sources', [])), reverse=True)[:3]
    packet['interview'] = dict(schema='interview-preparation/v1', contextSha256='', preparedOn=packet['updatedAt'],
        target=None, headline=draft['profile'].get('heading') or 'Your work, in conversation',
        throughline=draft['profile'].get('focus') or packet['person']['overview'],
        signals=[dict(title=a['title'], reason=a.get('reason') or a.get('problem') or a['title'], storyId=a['id']) for a in leads],
        stories=stories, opening=[p for p in draft['profile'].get('intro', packet['person']['overview']).split('\n\n') if p.strip()],
        questions=questions, priorityGap=None,
        introOptions=[{'title': o['title'], 'text': o['text']} for o in draft['profile'].get('introOptions', [])])
    packet['interview']['contextSha256'] = renderer.sections.evidence_fingerprint(packet)
    packet['reviewStatus'] = 'draft'
    renderer.validate(packet)
    return packet


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('context', type=Path)
    parser.add_argument('notebook', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    if args.output.exists() or args.output.is_symlink(): parser.error('Choose a new output path')
    if args.notebook.stat().st_size > renderer.MAX_DOCUMENT_BYTES: parser.error('Notebook exceeds 64 MiB')
    packet = renderer.load_packet(args.context)
    for account in packet['accounts']:
        for artifact in account.get('artifacts', []):
            mime, raw = renderer.image_data(artifact, args.context.parent)
            artifact.pop('file', None)
            artifact.update(mediaType=mime, sha256=hashlib.sha256(raw).hexdigest(),
                            _dataUrl='data:' + mime + ';base64,' + base64.b64encode(raw).decode())
    reader = NotebookReader(); reader.feed(args.notebook.read_text(encoding='utf-8'))
    result = merge(packet, json.loads(''.join(reader.parts)))
    with args.output.open('x', encoding='utf-8') as stream: json.dump(result, stream, ensure_ascii=True, indent=2)
    print(json.dumps({'path': str(args.output), 'accounts': len(result['accounts']), 'periods': len(result['timeline']),
                      'stories': len(result['interview']['stories']), 'sources': len(result['sources'])}))


if __name__ == '__main__': main()
