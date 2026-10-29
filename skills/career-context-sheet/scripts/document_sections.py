"""Timeline and interview views for the single portable career document."""
import copy
import hashlib
import html
import json
import re


def evidence_fingerprint(packet):
    """Ignore presentation, image transport and rehearsal edits, not evidence."""
    evidence = {k: copy.deepcopy(packet[k]) for k in
                ('person', 'profile', 'accounts', 'sources', 'timeline') if k in packet}
    for account in evidence['accounts']:
        account.pop('artifacts', None)
    return hashlib.sha256(json.dumps(evidence, sort_keys=True, ensure_ascii=True,
                                    separators=(',', ':')).encode()).hexdigest()


def validate_timeline(packet, check_text, keys):
    timeline = packet.get('timeline', [])
    if not isinstance(timeline, list) or len(timeline) > 240:
        raise ValueError('Timeline must contain at most 240 periods')
    source_ids = {s['id'] for s in packet['sources']}
    account_ids = {a['id'] for a in packet['accounts']}
    ids, used = set(), set()
    for period in timeline:
        keys(period, ['id', 'period', 'title', 'focus', 'actions', 'tension',
                      'approach', 'questions', 'sourceRefs', 'accountIds'], 'Timeline period')
        key = period.get('id')
        if not isinstance(key, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,99}', key) or key in ids:
            raise ValueError('Timeline periods need unique safe IDs')
        ids.add(key)
        for field in ['period', 'title', 'focus', 'tension', 'approach']:
            check_text(period.get(field), 'Timeline ' + field, 15000)
        for field in ['period', 'title']:
            if not period[field].strip(): raise ValueError('Timeline ' + field + ' must not be blank')
        for field in ['actions', 'questions', 'sourceRefs', 'accountIds']:
            if not isinstance(period.get(field), list) or len(period[field]) > 300:
                raise ValueError('Timeline ' + field + ' must be a bounded list')
            for value in period[field]: check_text(value, 'Timeline ' + field, 15000)
        for field, allowed in [('sourceRefs', source_ids), ('accountIds', account_ids)]:
            if len(set(period[field])) != len(period[field]) or set(period[field]) - allowed:
                raise ValueError('Timeline ' + field + ' must resolve without duplicates')
        if not period['sourceRefs']: raise ValueError('Every timeline period needs source references')
        used.update(period['sourceRefs'])
    return used


def validate_rehearsal(packet, check_text, keys):
    rehearsal = packet.get('rehearsal')
    if rehearsal is None: return
    keys(rehearsal, ['updatedAt', 'notes'], 'Rehearsal')
    if not isinstance(rehearsal.get('updatedAt'), int) or isinstance(rehearsal['updatedAt'], bool) or rehearsal['updatedAt'] < 0:
        raise ValueError('Rehearsal needs a nonnegative update time')
    ids = {s['id'] for s in packet.get('interview', {}).get('stories', [])}
    notes = rehearsal.get('notes')
    if not isinstance(notes, dict) or set(notes) - ids:
        raise ValueError('Rehearsal notes must reference prepared stories')
    for note in notes.values(): check_text(note, 'Rehearsal note', 15000)


def esc(value):
    return html.escape(str(value), quote=True)


def paragraphs(value):
    return ''.join('<p>' + esc(p) + '</p>' for p in value.split('\n\n') if p.strip())


def bullets(values):
    return '<ul>' + ''.join('<li>' + esc(v) + '</li>' for v in values) + '</ul>' if values else ''


def references(packet, ids):
    names = {s['id']: s['label'] for s in packet['sources']}
    return '<div class="section-references">' + ''.join(
        f'<a href="#source-{esc(key)}">{esc(names[key])}</a>' for key in ids) + '</div>'


def timeline_html(packet):
    periods = packet.get('timeline', [])
    if not periods:
        return '<p class="empty">No dated career timeline recorded yet. Add supported periods from your work history.</p>'
    accounts = {a['id']: a for a in packet['accounts']}
    stories = {s['id'] for s in packet.get('interview', {}).get('stories', [])}
    index, body = [], []
    for ordinal, period in enumerate(periods):
        key = esc(period['id'])
        index.append(f'<a href="#quarter-{key}"><span>{esc(period["period"])}</span>{esc(period["title"])}</a>')
        work = ''.join(f'<a href="#account-{esc(aid)}">{esc(accounts[aid]["title"])} <span aria-hidden="true">↗</span></a>'
                       for aid in period['accountIds'])
        practice = ''.join(f'<a href="#prep-story-{esc(aid)}">Practise this story <span aria-hidden="true">→</span></a>'
                           for aid in period['accountIds'] if aid in stories)
        next_links = ''.join(f'<a href="#quarter-{esc(periods[i]["id"])}">{label} {esc(periods[i]["period"])}</a>'
                             for i, label in [(ordinal - 1, '←'), (ordinal + 1, '→')] if 0 <= i < len(periods))
        readings = ''.join(f'<section><h4>{label}</h4>{paragraphs(period[field])}</section>'
                           for field, label in [('tension', 'Pressure & limits'), ('approach', 'Change in approach')]
                           if period[field])
        body.append(f'''<article class="quarter-reading" id="quarter-{key}" tabindex="-1">
<span class="period">{esc(period['period'])}</span><h3>{esc(period['title'])}</h3>
<div class="quarter-focus">{paragraphs(period['focus'])}</div>
<details class="section-detail" open><summary>The work</summary>{bullets(period['actions'])}</details>
<div class="quarter-interpretation">{readings}</div>
<details class="section-detail"><summary>Sources &amp; open questions</summary>{bullets(period['questions'])}{references(packet, period['sourceRefs'])}</details>
<div class="related-work">{work}{practice}</div><nav class="period-next" aria-label="Adjacent career periods">{next_links}</nav></article>''')
    return ('<div class="timeline-layout"><nav class="period-index" aria-label="Career periods">' + ''.join(index) +
            '</nav><div class="timeline-readings">' + ''.join(body) + '</div></div>')


def interview_html(packet):
    prep = packet.get('interview')
    if prep is None:
        return '<p class="empty">Interview preparation has not been drafted yet. Use the work accounts to prepare an opening and supported answers.</p>'
    accounts = {a['id']: a for a in packet['accounts']}
    options = ''.join(f'<option value="{esc(s["id"])}">{esc(accounts[s["id"]]["title"])}</option>' for s in prep['stories'])
    signals = ''.join(f'<li><a href="#prep-story-{esc(s["storyId"])}">{esc(s["title"])}</a><p>{esc(s.get("summary",s["reason"]))}</p></li>' for s in prep['signals'])
    intro_options = ''.join(f'<details class="section-detail"><summary>{esc(o["title"])}</summary>{paragraphs(o["text"])}</details>' for o in prep.get('introOptions', []))
    opening = ''.join(paragraphs(p) for p in prep['opening'])
    body = []
    for story in prep['stories']:
        account, key = accounts[story['id']], esc(story['id'])
        chapters = ''.join(f'<li><h4>{esc(c["title"])}</h4>{paragraphs(c["text"])}</li>' for c in story['chapters'])
        pace = ''.join(f'<li><span class="period">{esc(m["when"])}</span>{paragraphs(m["text"])}</li>' for m in story['timeline'])
        questions = ''.join(f'''<details class="section-detail answer" open><summary>{esc(q['question'])}</summary>
<p class="question-tests">{esc(q['tests'])}</p>{paragraphs(q['answer'])}
<details class="answer-reason"><summary>Why this example</summary>{paragraphs(q['reason'])}</details></details>'''
                            for q in prep['questions'] if q['storyId'] == story['id'])
        note = packet.get('rehearsal', {}).get('notes', {}).get(story['id'], story.get('practice', ''))
        body.append(f'''<article class="prep-story" id="prep-story-{key}" tabindex="-1">
<span class="period">{esc(account['period'])}</span><h3>{esc(account['title'])}</h3>
<p class="story-takeaway">{esc(story['takeaway'])}</p>{questions}
<details class="section-detail"><summary>Story chapters</summary><ol class="story-chapters">{chapters}</ol></details>
<details class="section-detail"><summary>Sequence &amp; pace</summary><ol class="story-pace">{pace}</ol></details>
<div class="prep-credit"><h4>Shared work &amp; limits</h4>{paragraphs(account['sharedCredit'])}{bullets(account['limits'])}</div>
<details class="section-detail"><summary>What to sharpen</summary>{paragraphs(story.get('practice', ''))}{bullets(account['questions'])}
<label class="rehearsal-editor js-only" for="rehearsal-{key}">Private rehearsal note<textarea id="rehearsal-{key}" data-rehearsal="{key}" maxlength="15000" rows="4">{esc(note)}</textarea></label></details>
<div class="no-script" data-rehearsal-display="{key}">{paragraphs(note)}</div>
<div class="related-work"><a href="#account-{key}">Work account &amp; sources <span aria-hidden="true">↗</span></a></div></article>''')
    target = '<p class="period">' + esc(prep['target']) + '</p>' if prep['target'] else ''
    gap = prep['priorityGap']
    gap_html = (f'<details class="section-detail"><summary>One question to resolve</summary><h4>{esc(gap["question"])}</h4>{paragraphs(gap["why"])}</details>') if gap else ''
    return f'''<div class="prep-layout"><aside class="prep-index"><h3>Start with</h3><ol>{signals}</ol>
<details class="section-detail"><summary>Why these stories</summary>{paragraphs(prep['throughline'])}</details>
<details class="section-detail"><summary>Practice guide</summary><ol><li>Start with the opening. Choose the story that answers the actual question.</li><li>Explain the situation, your decision and your part. Keep shared work explicit.</li><li>Give the result and its limits, then pause. Use the chapters when asked for detail.</li><li>Record anything you could not explain. Keep unverified details as questions.</li></ol></details>
<button class="text-button js-only" id="copy-prep" type="button">Copy interview prep <span aria-hidden="true">↗</span></button>
<p id="prep-status" class="status" role="status"></p></aside><div class="prep-reading">
{target}<details class="opening section-detail" open><summary>Tell me about yourself</summary><div class="opening-text">{opening}</div>
{('<details class="section-detail"><summary>Alternative openings</summary>'+intro_options+'</details>') if intro_options else ''}</details>
<label class="story-picker js-only" for="prep-story-select">Practise a story<select id="prep-story-select">{options}</select></label>
{''.join(body)}{gap_html}</div></div>'''
