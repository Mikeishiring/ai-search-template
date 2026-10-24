"""Manual first-attempt source assessment; no model retry or protocol changes."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;folder=ROOT/'runs/completion'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
gold=read(ROOT/'fixtures/completion.gold.json');corpus=read(ROOT/'fixtures/completion.corpus.json')
review=read(folder/'researcher/review.json');trace=read(folder/'trace.json');provenance=read(folder/'provenance.json')
judgements={
 'theme-01':('pass',['C3','C4','C5'],'Credits the subject with the proposal, alignment command, confidence reporting, overlap prevention, provenance, configuration and tests. Keeps player and content ownership separate.'),
 'theme-02':('pass',['C4'],'Defines the 0.42-second median over 68 reviewed boundaries in four recordings, with two poor music sections and no claim that all twelve recordings were validated.'),
 'theme-03':('partial',['C5'],'Names Contributor 07’s review requests and the subject’s corrections, but leaves the deeper approval reply unread. That reply explicitly distinguishes tool-path approval from editorial validation. The model reports the gap instead of inventing a review result.'),
 'theme-04':('pass',['C6','C7','C9','C12'],'The account preserves regeneration, stale-master detection and rerun, documentation, the fixture supplied for a player repair and operational follow-through. It avoids claiming the subject personally approved all content. The guide itself is treated as contextual rather than directly quoted.'),
 'theme-05':('pass',['C1','C6','C9','C10'],'Separates editorial corrections and listening, export support, player fixes, code review and programme release authority. The final account carries these roles rather than crediting the whole release to the subject.'),
 'theme-06':('pass',['C10'],'Keeps the ten-of-twelve release and continued use through June, and explicitly excludes the two recordings awaiting curatorial transcript approval from the subject’s responsibility.'),
 'theme-07':('pass',['C9'],'Credits player flicker and seek-state repairs to Contributor 04. Limits the subject’s contribution to supplying a fixture and preserves the evidence that seeking problems reproduced independently of cue generation.'),
 'theme-08':('partial',['C8','C14'],'Distinguishes an internal walkthrough from visitor research and a manual editorial split from a general tool fix, with only one quiet shift afterwards. However, the final account and claims do not credit the subject’s investigation of recording D or suggestion of that split, despite reading chat:014 in full. Early host observations are also compressed away.'),
 'theme-09':('pass',['C10','C11'],'Preserves ten recordings remaining in use, no cancellations caused by the player, and the eleven voluntary comments over roughly 510 starts across seven sessions. Keeps the category breakdown and declines to infer a true error rate or visitor impact.'),
 'theme-10':('pass',['C12'],'Finds the single staff-training reuse with only flagged sections reviewed, distinguishes reuse from broad adoption, and retains the lack of a permanent-collection migration decision.'),
 'theme-11':('pass',['C13'],'Reports only the two-editor qualitative effort claim with no time tracking. The survey was explicitly unavailable, so the claim rests on the retrospective summary rather than an invented saving or an imagined survey result.'),
 'theme-12':('pass',['C3','C4','C8'],'Retains weak music and overlapping-speaker timing, visible confidence flags and human editorial review. Does not turn a plausible timing output or a manual content judgment into autonomous accuracy.')
}
records=read(folder/'result.json')['records'];read_ids={r['id'] for r in records};themes=[]
for t in gold['themes']:
    status,ids,assessment=judgements[t['id']]
    assert all(any(c['id']==id for c in review['claims']) for id in ids)
    themes.append(dict(t,status=status,claim_ids=ids,assessment=assessment,unread_anchors=[id for id in t['anchors'] if id not in read_ids]))
events=trace['events'];receipt=trace['completion_receipt'];plan=trace['planning']
claims={c['id']:c for c in review['claims']}
used_without_quote=[]
for d in review['evidence_dispositions']:
    if d['disposition']=='used':
        cited={e['record_id'] for id in d['claim_ids'] if id in claims for e in claims[id]['evidence']}
        used_without_quote.extend(sorted(set(d['record_ids'])-cited))
contexts={e['arguments']['id'] for e in events if e['tool']=='read_context' and e['result'].get('end_reached')}
sweeps={(e['arguments']['source'],e['arguments']['window']) for e in events if e['tool']=='list_roots' and e['result'].get('end_reached')}
counts={'fully_met':sum(t['status']=='pass' for t in themes),'partial':sum(t['status']=='partial' for t in themes),'missed':sum(t['status']=='missed' for t in themes),'themes':len(themes),'full_records':len(read_ids),'accessible_records':len(gold['expected_records']),'source_calls':trace['source_calls'],'requests':trace['requests'],'cache_hits':trace['cache_hits'],'remaining_source_calls':plan['calls_remaining'],'completed_contexts':len(contexts),'unfinished_contexts':len(plan['unopened_contexts']),'completed_source_window_sweeps':len(sweeps),'unread_surfaced_records':len(plan['unread_surfaced_records']),'unchecked_attachments':len(plan['unchecked_attachments']),'exact_spans':provenance['quote_count'],'submitted_spans':sum(len(c['evidence']) for c in review['claims']),'completion_receipt_valid':provenance['completion_receipt_valid'],'validation_flags':len(provenance['errors']),'disposition_records':provenance['disposition_records'],'attribution_chains':provenance['attribution_chains']}
assessment={
 'headline':'The stop was honest. The research remained incomplete.',
 'summary':'All surfaced standalone records were read before judging relevance. All 43 selected source spans resolve exactly. The researcher stopped at the real source limit, leaving a deeper review reply and an export attachment unchecked; one personal contribution was still lost during synthesis.',
 'scope_limit':'One untouched museum-audio story from a separate AI author; one uncoached research attempt. Ten of twelve themes fully met and two partly met. The completion receipt is valid, but four attribution/disposition checks fail. This is not an end-to-end pass.',
 'expected_records':len(gold['expected_records']),'themes':themes,
 'issue_heading':'Exact quotations do not guarantee a complete account.',
 'issues':[
  {'severity':'Deep reply not reached','claim_ids':['C5'],'detail':'The final queue names repo:005 as having unopened context. Its child repo:006 approves the changed tool path while withholding broader editorial validation. The model spent its last charged call checking the unavailable survey, leaving this nested review reply uninspected. It disclosed the gap accurately.'},
  {'severity':'Personal investigation omitted','claim_ids':['C8'],'detail':'In chat:014, the subject checks recording D against the released master, explains why changing the algorithm will not fix simultaneous speakers, and proposes a manual split. The record was read but labeled contextual. The final story mentions the split without preserving this personal diagnostic work.'},
  {'severity':'Evidence ledger inconsistent','claim_ids':['C5','C6'],'detail':'Three records—chat:005, chat:011 and chat:016—are marked used without a linked quotation. repo:005 appears as both used and unresolved, conflating a read record with its unread child. One role’s source, docs:001, is outside its chain’s linked claims. The validator retains all of these failures.'},
  {'severity':'Unchecked attachment in checked-file ledger','claim_ids':['C6','C12'],'detail':'The model included att:export-sample in attachment_dispositions despite never opening it. Its reason truthfully says it was not inspected, but that field is for checked attachments. The source remains an explicit unresolved item; no contents were fabricated.'},
  {'severity':'Coverage costs calls','claim_ids':[],'detail':'The conservative rule made the model read the film-night, scanner-outage and recorder-maintenance records before excluding them. It also spent 14 calls enumerating three windows across three sources. This prevents snippet-only dismissal but leaves a prioritisation tradeoff under a fixed budget; it is not a scalable relevance strategy by itself.'}
 ],
 'limitations':[
  'The author received only a generic synthetic brief plus diversity requirements: a domain outside warehouse/logistics and cooling, three distractors and a material nested reply. The 40-record story was accepted unchanged. No prior story, private record, implementation or researcher prompt was supplied.',
  'Author and researcher used the same provider/default model family; the exact model identifier was not captured. The new setting is museum transcript alignment, but the author reused the fictional project name. Separate AI sessions do not establish human-level benchmark independence.',
  'This assistant manually assessed the twelve hidden author-defined themes after the first response. Ten full and two partial measures interpreted coverage for this case, separately from structural validation. It is not a general reliability estimate.',
  '38 of 39 accessible primary records were read. The remaining record is an approval nested beneath three prior repository messages; it was not returned as a snippet. One additional record lies beyond the horizon. All three distractors were fully read, then excluded.',
  'All 43 cited spans resolve to exact text from records returned in full. The AI chose the spans; the local compiler supplied their text. This prevents altered punctuation in evidence quotations but does not validate claim relevance, paraphrases or narrative completeness.',
  'The final receipt matches 45 charged calls and 47 total requests, with zero source calls remaining. There was one finish check, accepted as source_limit. The model did not attempt an early check in this story; unit tests demonstrate rejection of premature completion.',
  'The receipt certifies the stopping state of observed evidence, not exhaustive discovery or semantic quality. It expressly retains one unopened context and one unchecked attachment. The raw response and receipt are preserved alongside the compiled citation view.',
  'Four structural checks fail: used records lacking quotations, a duplicate record disposition, a role source outside its linked claims, and an unchecked attachment in the checked-file ledger. None was patched into a passing result.',
  'The model read the nested stale-master clarification and manual-split follow-up but did not finish the deeper review chain. Genuine nesting was exercised; search and out-of-window query broadening were not used. The earlier 90-day sweep was empty, and pre-existing context came from the project brief.',
  'The available export attachment remains unchecked and the survey is explicitly unavailable. No source supports quantified labour savings or formal accessibility improvement. Source metrics are retained reports, not independently recomputed telemetry.',
  'The completion gate, source-span protocol, free local audits, larger request ceiling and different story all changed. The theme score cannot isolate the effect of any one change. No private archive or live online source was accessed.'
 ],
 'method':'The implementation, prompts, schemas, completion and span validator were frozen before a separate AI authored the story. A fresh researcher selected every MCP request and source span. Its first response was saved, then the local compiler resolved span IDs and checked the final receipt. This assistant opened the hidden rubric only after research ended and assessed the original sources; there was no coaching, retest or fixture edit.',
 'next_experiment':'Test budget allocation across deeper replies and peripheral records on another untouched case. Generate evidence dispositions and chain cross-references from selected spans rather than free-form lists, while separately testing whether personal diagnostic work survives the final narrative. Keep this result unchanged.',
 'summary_counts':counts,'final_planning':plan,'completion_receipt':{k:v for k,v in receipt.items() if k!='planning'},'validation_errors':provenance['errors'],'used_without_linked_quote':used_without_quote,
 'adjudicator':'This assistant; manual comparison with separate-author rubric and original sources','substantive_attempts':1,'content_edited':False,'prompt_frozen':True,'private_records_supplied':False,
 'raw_response_sha256':hashlib.sha256((folder/'researcher/response.json').read_bytes()).hexdigest(),'compiled_review_sha256':hashlib.sha256((folder/'researcher/review.json').read_bytes()).hexdigest(),'gold_sha256':hashlib.sha256((ROOT/'fixtures/completion.gold.json').read_bytes()).hexdigest()
}
assert (counts['fully_met'],counts['partial'])==(10,2)
assert counts['exact_spans']==counts['submitted_spans']==43 and counts['completion_receipt_valid']
assert counts['validation_flags']==4 and counts['remaining_source_calls']==0
(folder/'assessment.json').write_text(json.dumps(assessment,indent=2,ensure_ascii=False),encoding='utf-8')
attachments=[]
for a in corpus['attachments']:
    calls=[e for e in events if e['tool']=='read_attachment' and e['arguments']['id']==a['id']]
    attachments.append(a|{'read_by_researcher':bool(calls),'observed_result':calls[-1]['result'].get('reason','Full attachment returned') if calls else 'Evaluator copy; not checked during research.'})
(folder/'attachments.json').write_text(json.dumps(attachments,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(counts))
