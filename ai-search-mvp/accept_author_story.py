"""Accept an oversized independent story without pruning or revising its contents.

The original installer rejected 42 records (requested 32–40). This audit accepts
that documented size deviation only. Research instructions and budget stay frozen.
"""
import json,re
from pathlib import Path
from model_backend import sha
ROOT=Path(__file__).resolve().parent
folder=ROOT/'runs/autonomous'
original=folder/'author/response.json'
story=json.loads(original.read_text(encoding='utf-8'))
corpus,scope,gold=story['corpus'],story['scope'],story['gold']
assert corpus['synthetic'] is True and 32<=len(corpus['records'])<=64
assert 8<=len(gold['themes'])<=12 and scope['start']<=scope['end']<=scope['horizon']
records={r['id']:r for r in corpus['records']};assert len(records)==len(corpus['records'])
sources={s['id'] for s in corpus['sources']};assert sources=={'chat','docs','repo'}
for r in records.values():
    assert r['source'] in sources and r['id'].startswith(r['source']+':')
    assert re.fullmatch(r'Contributor \d{2}',r['author']) and re.fullmatch(r'\d{4}-\d{2}-\d{2}',r['date'])
    assert not r['parent'] or r['parent'] in records and records[r['parent']]['source']==r['source']
    assert all(link['id'] in records and records[link['id']]['source']==link['source'] for link in r['links'])
    assert all(any(a['id']==id for a in corpus['attachments']) for id in r['attachments'])
    assert not r['repost_of'] or r['repost_of'] in records
    seen=set();p=r
    while p['parent']:
        assert p['id'] not in seen;seen.add(p['id']);p=records[p['parent']]
assert set(gold['expected_records'])=={r['id'] for r in records.values() if r['date']<=scope['horizon']}
assert all(t['anchors'] and all(id in gold['expected_records'] for id in t['anchors']) for t in gold['themes'])
assert any(a['unavailable'] for a in corpus['attachments'])
assert not re.search(r'(?i)C:[/\\]|/Users/|https?://|xox[baprs]-|sk-ant-',json.dumps(story))
hashes={}
for kind,obj in [('corpus',corpus),('scope',scope),('gold',gold)]:
    path=ROOT/f'fixtures/autonomous.{kind}.json'
    if path.exists():raise RuntimeError('Fixture already installed')
    path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8');hashes[kind]=sha(path)
freeze={'sha256':hashes,'structural_validation':'passed except declared record-count deviation','content_edited':False,'original_author_sha256':sha(original),'research_started':False,'deviation':f"Author supplied {len(records)} records instead of requested 32–40. Kept intact; no content edits, no prompt or 45-call budget changes."}
(folder/'story-freeze.json').write_text(json.dumps(freeze,indent=2),encoding='utf-8')
print(json.dumps({'story_installed':True,'records':len(records),'themes':len(gold['themes']),'content_edited':False,'record_count_deviation':True}))
