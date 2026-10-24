"""Manual source-based assessment of the first autonomous attempt; no model retest."""
import json,hashlib
from pathlib import Path
from autonomous_server import ResearchSource
ROOT=Path(__file__).resolve().parent
folder=ROOT/'runs/autonomous'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
gold=read(ROOT/'fixtures/autonomous.gold.json');corpus=read(ROOT/'fixtures/autonomous.corpus.json');scope=read(ROOT/'fixtures/autonomous.scope.json')
review=read(folder/'researcher/response.json');trace=read(folder/'trace.json');provenance=read(folder/'provenance.json')
assert provenance['valid'] and trace['source_calls']==45
judgements={
 'theme-01':('pass',['claim-01','claim-02'],'Preserves a testable overlap hypothesis and the competing door-open explanation. Does not claim the subject originated the incident report or proved causality.'),
 'theme-02':('pass',['claim-03','claim-04'],'Credits the parser, overlap detector and simulator to the subject, while preserving the defect and the other contributor’s discovery and fixture. The acknowledgement reply was not read, but the correction and review were.'),
 'theme-03':('pass',['claim-02','claim-05'],'Captures the bounded, supervised pilot, stop conditions, excluded interval and reduction from six planned nights to four staffed nights. Separates proposal, safety constraints and operations authority.'),
 'theme-04':('pass',['claim-06'],'Accurately describes recommendation mode and review-driven safety changes without turning the interface into automatic controller commands.'),
 'theme-05':('partial',['claim-07','claim-08'],'Keeps the four-night 38 kW observation, unchanged energy, operator intervention and safety limits. Misses the concrete operational count: eligible overlaps fell from 11 to 3. That count was in an unread reply under the first trial-night message.'),
 'theme-06':('pass',['claim-08','claim-09'],'Keeps the lower door-open time as a confounder and preserves the explicit correction to sole credit. Does not present the 38 kW difference as a controlled saving.'),
 'theme-07':('partial',['claim-11','claim-13'],'Finds the R4 constraint, unit risk and two manual trial nights via repository and quarterly records. Does not read the trial message explaining that the second night had too few eligible cycles to compare, so its account loses a material limitation.'),
 'theme-08':('pass',['claim-10'],'Credits the operating guide to the subject while retaining the operations edits and the clarification that confirmation is not autonomous approval.'),
 'theme-09':('pass',['claim-15'],'Preserves the subject’s cautious outcome wording, unchanged energy, no annualisation and unknown tariff benefit. Does not invent money saved.'),
 'theme-10':('pass',['claim-12'],'Finds the later 30-second disconnected-state correction, fresh recalculation and tests, while keeping the separate R4 blocker unresolved.'),
 'theme-11':('partial',['claim-13','claim-14'],'Finds the later R4 clarification and continued lack of second-site prioritisation. Misses the February 2028 selected-night use report and June horizon summary. It therefore calls first-site continuation unknown even though accessible records answer part of that question. The logs still do not establish broad or measured adoption.'),
 'theme-12':('pass',[],'Does not rely on the unavailable appendix or the post-horizon controller decision. This is a pass for the rubric’s non-reliance requirement, not proof of discovery: it never read the document referencing the missing attachment and made no attachment call.')
}
themes=[]
read_ids={r['id'] for r in read(folder/'result.json')['records']}
for t in gold['themes']:
    status,claim_ids,assessment=judgements[t['id']]
    assert all(any(c['id']==id for c in review['claims']) for id in claim_ids)
    themes.append(dict(t,status=status,claim_ids=claim_ids,assessment=assessment,unread_anchors=[id for id in t['anchors'] if id not in read_ids]))

# Post-run diagnostic probes use a separate journal and never reach the researcher.
probe_path=folder/'audit-probes.jsonl'
if not probe_path.exists():
    server=ResearchSource(corpus,scope,probe_path)
    for tool,args in [('read_context',{'source':'chat','id':'chat:007'}),('search',{'source':'docs','query':'Lantern'}),('read_record',{'source':'docs','id':'docs:011'}),('read_record',{'source':'chat','id':'chat:012'}),('read_record',{'source':'docs','id':'docs:007'}),('read_attachment',{'source':'docs','id':'att:001'})]:server.execute(tool,args)
probes=[json.loads(line) for line in probe_path.read_text(encoding='utf-8').splitlines()]
server=ResearchSource(corpus,scope,probe_path)
search_pages=[p for p in server.events if p['tool']=='search']
cursor=search_pages[-1]['result'].get('next_cursor')
while cursor:
    page=server.execute('search',{'source':'docs','query':'Lantern','cursor':cursor})
    cursor=page.get('next_cursor')
probes=server.events
assert [r['id'] for r in probes[0]['result']['items']]==['chat:008','chat:016']
assert any(r['id']=='docs:011' for p in probes if p['tool']=='search' for r in p['result']['items'])
assert any(p['result'].get('unavailable') for p in probes if p['tool']=='read_attachment')
events=trace['events']
seen={r['id'] for event in events for r in event['result'].get('items',[]) if 'parent' in r}
accessible={r['id'] for r in corpus['records'] if r['date']<=scope['horizon']}
unopened=[r['id'] for r in corpus['records'] if r['id'] in read_ids and any(child['parent']==r['id'] and child['date']<=scope['horizon'] and child['id'] not in read_ids for child in corpus['records'])]
assessment={
 'headline':'It understood the work it read. It missed later use.',
 'summary':'The researcher chose its own searches across three platforms. It preserved shared ownership and cautious outcome claims, but skipped replies containing an operational result and continued use.',
 'scope_limit':'One untouched story from a separate AI author; one uncoached research attempt. The same model provider was used for author and researcher. This is not an independent human benchmark.',
 'expected_records':len(gold['expected_records']),'themes':themes,
 'issue_heading':'An honest unknown can still be a research miss.',
 'issues':[
  {'severity':'Unopened thread','claim_ids':['claim-07','claim-08'],'detail':'The model read chat:007 but did not expand it. One context read would have returned both the 11-to-3 operational count (chat:008) and selected-night use in February 2028 (chat:016). This is an observed retrieval miss, not a hypothetical gap.'},
  {'severity':'Search scope','claim_ids':['claim-13','claim-14'],'detail':'Root enumeration covers activity in the original question window. The model never broadened its failed document query from “Project Lantern” to “Lantern”. A post-run audit found the June 2028 horizon summary on the fourth page of that broader search. The search contract, pagination cost and model’s query choices all contributed to the gap.'},
  {'severity':'Sample quality omitted','claim_ids':['claim-11','claim-13'],'detail':'The quarterly summary gave two manual second-site nights, but the unread trial record says the second night had too few eligible cycles to compare. The model reported the count without this limitation.'},
  {'severity':'Uninspected mandate and attachment','claim_ids':['claim-13'],'detail':'docs:007 stayed snippet-only. The researcher missed the condition requiring eight additional busy-loading nights before fleet automation, and did not discover its unavailable vendor appendix. Avoiding unsupported attachment claims is not the same as auditing missing evidence.'},
  {'severity':'Budget allocation','claim_ids':[],'detail':'Six initial searches included four empty results. The model then spent 17 calls reading individual roots and exhausted all 45 calls, leaving one search continuation open and two read roots with unread replies. It did not fabricate completeness, but its coverage accounting did not identify these unopened threads.'}
 ],
 'limitations':[
  'Separate author session received only a generic authoring brief and schema, with no private data, old fixtures, implementation or researcher prompt. The author and researcher still used the same provider/default model family, so this is weaker independence than a separately recruited human author.',
  'The author returned 42 records rather than the requested 32–40. The original content was preserved; the 45-call limit and research prompt were not changed. Of those records, 41 are accessible through the horizon and one is later.',
  'This assistant manually assessed the answer against the author’s 12-theme rubric. Nine themes are fully met and three partly met; the categories are judgement calls, not a general accuracy estimate.',
  'The rubric is comparatively explicit and the story contains only one unrelated distractor. It is not a stress test of large, noisy workplace archives or ambiguous identity resolution.',
  'The 31-of-41 read count includes all accessible records, including distractors. It is an inventory measure, not the fraction of relevant context understood. Five records were seen only as snippets and five were not surfaced at all.',
  'Root enumeration is bounded to the original question window; search and context reads extend through the horizon. A production planner needs an explicit follow-up-window inventory rather than relying only on its initial root listing.',
  'All 27 quotations match original records actually read by the model. This validates citation provenance, not every interpretation. No fabricated quantified result was found in this assessment.',
  'Post-run diagnostic probes used the hidden rubric to locate omissions. They were never fed to the researcher, are not a second model attempt, and do not establish that the model would choose those probes unaided.',
  'Only simulated source adapters were used. No live Slack, Notion, GitHub, calendar or private record was accessed. Inference used the authenticated Codex service; outputs and evidence are stored locally.',
  'The precise model identifier was not captured by the CLI receipt. Repeatability across model versions is untested.'
 ],
 'method':'A separate isolated Codex session wrote the story and hidden rubric. The research prompt, source tools, page size of three and 45-call limit were frozen before authoring. The researcher started with scope only and selected every source call. The answer was preserved before this assistant opened the rubric; exact spans and content hashes were then checked.',
 'next_experiment':'On another independently authored case, test a planner that reserves calls for observed reply flags and a separate follow-up-window inventory. Keep this run as the failure baseline; do not retune it into a passing example.',
 'summary_counts':{'fully_met':9,'partial':3,'missed':0,'themes':12,'full_records':len(read_ids),'snippet_only':len(seen-read_ids),'unseen':len(accessible-seen),'source_calls':len(events),'searches':trace['searches'],'pending_pages':len(trace['pending_pages']),'read_roots_with_unread_children':len(unopened),'quotes':provenance['quote_count']},
 'unopened_context_roots':unopened,
 'adjudicator':'This assistant; manual comparison against separate-author rubric and original sources',
 'substantive_attempts':1,'content_edited':False,'prompt_frozen':True,'private_records_supplied':False,
 'review_sha256':hashlib.sha256((folder/'researcher/response.json').read_bytes()).hexdigest(),
 'gold_sha256':hashlib.sha256((ROOT/'fixtures/autonomous.gold.json').read_bytes()).hexdigest(),
 'post_run_audit_probe_count':len(probes)
}
assert sum(t['status']=='pass' for t in themes)==9 and sum(t['status']=='partial' for t in themes)==3
(folder/'assessment.json').write_text(json.dumps(assessment,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(assessment['summary_counts']))
