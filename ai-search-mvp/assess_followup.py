"""Post-run manual assessment. Does not modify or re-invoke the frozen researcher."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent
folder=ROOT/'runs/followup'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
gold=read(ROOT/'fixtures/followup.gold.json');corpus=read(ROOT/'fixtures/followup.corpus.json')
review=read(folder/'researcher/response.json');trace=read(folder/'trace.json');provenance=read(folder/'provenance.json')
assert provenance['valid'] and trace['source_calls']==45
judgements={
 'theme-01':('pass',['c1','c2','c3'],'Credits the subject with the scoped mobile proposal and implementation. Keeps stock mutation out of scope and distinguishes the proposal from repository evidence. Route-explanation detail is compressed, but the contribution boundary is preserved.'),
 'theme-02':('pass',['c1','c3'],'Separates mobile support from the snapshot service, measurement and interviews; explicitly limits the subject’s backend contribution to fixture shape and compatibility review.'),
 'theme-03':('partial',['c3'],'Reports the implemented crossing penalty but omits the correction’s origin. Both docs:004 and chat:004 were read in full: Contributor 05 identified the forklift risk, and Contributor 01 acknowledged having modeled distance alone. The source was retrieved; the final account lost the feedback and initial mistake.'),
 'theme-04':('pass',['c4','c5'],'Preserves review-driven stale-data blocking, the lifecycle diagnosis and repair, and the limits of two-device bench testing. Does not claim initial safety or universal field reliability.'),
 'theme-05':('pass',['c6'],'Connects the incident reply to the shipped message, retry and instrumentation changes. Explains two of three devices while retaining the missing third log and unchanged authentication policy.'),
 'theme-06':('pass',['c7'],'Retains responsibility for the category-design error, the shipped assistance reason and the explicit break in comparability after shift four. Does not blame operators or treat the correction as erasing the earlier flaw.'),
 'theme-07':('pass',['c9'],'Preserves the three bounded pilot comparisons and six-versus-six morning scope. Limits and rejected conclusions retain workload, staffing, novelty and export freshness as competing explanations; no causal productivity claim is accepted.'),
 'theme-08':('pass',['c10','c11'],'Finds the later reply with seven of eight devices used on at least 14 of 18 mornings and the newly created August document reporting six working devices. Keeps paper fallback, inconsistent shift-duration measurement and no repeat time study explicit.'),
 'theme-09':('pass',['c8','c12'],'Connects the handover and capacity boundary to later implementation by Contributor 02. Does not turn the handover into a commitment by the subject or the deferred admin workflow into personal failure.'),
 'theme-10':('pass',['c6','c9','c11'],'Separates limited continued use from multi-depot rollout, leaves the third device unexplained, and does not infer accuracy gains, a causal effect or universal reliability. Does not use the September record beyond the horizon.'),
 'theme-11':('missed',['c9'],'Names export freshness as a pilot confounder, but never establishes that late exports predated the project. The January chat was never surfaced; the linked January baseline document was left unread. Avoiding blame is not the same as recovering the earlier context.')
}
records=read(folder/'result.json')['records'];read_ids={r['id'] for r in records}
themes=[]
for t in gold['themes']:
    status,claim_ids,assessment=judgements[t['id']]
    assert all(any(c['id']==id for c in review['claims']) for id in claim_ids)
    themes.append(dict(t,status=status,claim_ids=claim_ids,assessment=assessment,unread_anchors=[id for id in t['anchors'] if id not in read_ids]))
events=trace['events'];seen_full=set();redundant=[]
for e in events:
    ids={r['id'] for r in e['result'].get('items',[]) if e['result'].get('full_records')}
    if ids and ids<=seen_full:redundant.append({'sequence':e['sequence'],'tool':e['tool'],'ids':sorted(ids)})
    seen_full.update(ids)
plan=trace['planning']
contexts={e['arguments']['id'] for e in events if e['tool']=='read_context' and e['result'].get('end_reached')}
sweeps={(e['arguments']['source'],e['arguments']['window']) for e in events if e['tool']=='list_roots' and e['result'].get('end_reached')}
counts={'fully_met':sum(t['status']=='pass' for t in themes),'partial':sum(t['status']=='partial' for t in themes),'missed':sum(t['status']=='missed' for t in themes),'themes':len(themes),'full_records':len(read_ids),'snippet_only':len(trace['snippet_only_ids']),'unseen':len(trace['not_fully_read_ids'])-len(trace['snippet_only_ids']),'source_calls':len(events),'searches':trace['searches'],'pending_pages':len(trace['pending_pages']),'completed_contexts':len(contexts),'unfinished_contexts':len(plan['unopened_contexts']),'completed_source_window_sweeps':len(sweeps),'redundant_full_reads':len(redundant),'quotes':provenance['quote_count']}
assessment={
 'headline':'It followed later use. It still lost earlier context.',
 'summary':'The revised planner opened every discovered thread and found continued use months after the pilot. The final account omitted a review-driven safety correction and missed a problem that predated the project.',
 'scope_limit':'One new story from a separate AI session; one uncoached research attempt. Nine of eleven author-defined themes were fully met, one partly met and one missed. Different stories prevent a causal comparison with the earlier run.',
 'expected_records':len(gold['expected_records']),'themes':themes,
 'issue_heading':'Finishing the thread queue is not finishing the research.',
 'issues':[
  {'severity':'Read, then omitted','claim_ids':['c3'],'detail':'The model read the safety comment and the subject’s admission that distance alone had been modeled. Its final account mentioned the crossing penalty but omitted the reviewer’s contribution and the original mistake. This is a synthesis failure, not a retrieval failure.'},
  {'severity':'Earlier context missed','claim_ids':['c9'],'detail':'The pre-project export complaint in chat:001 was outside both enumerated windows and had no incoming link. No search was attempted. The linked baseline docs:001 was explicitly left unread. The model noted export age but did not establish that the problem predated the subject’s work.'},
  {'severity':'Three avoidable re-reads','claim_ids':[],'detail':'Calls 43–45 re-read chat:013, docs:009 and repo:014, all already returned in full. The queue still listed the earlier baseline and a results attachment. A visible queue helped thread coverage but did not prevent poor final budget allocation.'},
  {'severity':'Uninspected supporting files','claim_ids':['c5','c9'],'detail':'The available pilot table att:002 was not opened; the model disclosed this. It also left the device-log message chat:006 snippet-only and never discovered that att:001 was unavailable. The evaluator found that neither attachment changes the rubric conclusions, but the research did not establish that itself.'},
  {'severity':'Numbers remain secondary evidence','claim_ids':['c9'],'detail':'The synthetic results document reports totals and medians. Its attachment contains only a description of supporting rows, not the rows themselves. Even complete retrieval of this fixture could not independently recompute those metrics.'}
 ],
 'limitations':[
  'The author received only the generic story brief and schema. Planner, tool contract, page size and 45-call limit were frozen beforehand; the 38-record story was accepted without edits. The hidden rubric was opened only after the first research response was complete.',
  'Both sessions used the same provider/default model family. This is separate AI authorship, not an independent human benchmark; the precise model identifier was not captured.',
  'This assistant manually graded all eleven author-defined themes against the original records. Nine full, one partial and one missed is a judgement for this case, not an accuracy estimate.',
  'The 33-of-37 count includes all accessible records, including the kitchen distractor. Two records remained snippet-only and two were unseen in full or snippet. The remaining record is beyond the horizon.',
  'All eleven discovered contexts and all six source/window sweeps finished. The model found the April use reply and the new August follow-up document. This demonstrates those paths on this fixture, not exhaustive discovery across historical archives.',
  'The researcher made zero search calls. Query broadening was not exercised. The generated story has one irrelevant notice and no multi-level reply chain; unit tests cover nested expansion and context pagination, but this model run does not.',
  'All thirty quoted spans match records returned in full. Provenance checks do not establish that every statement is complete or that the fixture’s reported numbers can be recomputed.',
  'The planner lists observed obligations and asks the model to reserve budget. It does not force an action order, suppress duplicate reads or attach an explicit disposition to every skipped lead.',
  'All sources are simulated, read-only and offline. Only synthetic instructions and evidence were sent for model inference. No private archive or live platform was accessed.',
  'The earlier run remains unchanged. Different stories, denominators and rubrics mean the two theme scores cannot isolate the effect of the planner change.'
 ],
 'method':'A separate isolated AI author wrote the story and rubric after the revised planner was frozen. A fresh researcher received scope only, chose 45 MCP calls, and returned one preserved account. This assistant then inspected the hidden rubric and all source records; no evaluator discoveries were fed back and no model rerun occurred.',
 'next_experiment':'Freeze a planner with explicit dispositions for skipped leads, duplicate-read warnings and a bounded pre-project context sweep. Test another independently authored story with several distractors and genuinely nested threads; add a separate assessor and data that permits metric recomputation.',
 'summary_counts':counts,'redundant_reads':redundant,'final_planning':plan,
 'adjudicator':'This assistant; manual original-source comparison against separate-author rubric',
 'substantive_attempts':1,'content_edited':False,'prompt_frozen':True,'private_records_supplied':False,
 'review_sha256':hashlib.sha256((folder/'researcher/response.json').read_bytes()).hexdigest(),
 'gold_sha256':hashlib.sha256((ROOT/'fixtures/followup.gold.json').read_bytes()).hexdigest()
}
assert (counts['fully_met'],counts['partial'],counts['missed'])==(9,1,1)
(folder/'assessment.json').write_text(json.dumps(assessment,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(counts))
