"""Post-run original-source adjudication; preserves the first model output and failed checks."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;folder=ROOT/'runs/attribution'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
gold=read(ROOT/'fixtures/attribution.gold.json');corpus=read(ROOT/'fixtures/attribution.corpus.json')
review=read(folder/'researcher/response.json');trace=read(folder/'trace.json');provenance=read(folder/'provenance.json')
judgements={
 'theme-01':('pass',['C2'],'Separates the subject’s tablet queue, tests and service-test assistance from the endpoint, migration, firmware and physical labels. The final account preserves those ownership boundaries.'),
 'theme-02':('partial',['C2'],'Carries Contributor 03’s firmware constraint and the subject’s tablet-side adaptation into the account. It does not explicitly carry Contributor 02’s server uniqueness guard into the claim or narrative. The DM pair was read and labeled contextual; generic service ownership loses that specific joint design decision.'),
 'theme-03':('pass',['C3'],'The final story names Contributor 06 as the reviewer who found the battery-draining retry behavior, preserves the initial defect, and credits the subject with the ceiling, manual retry and rejection test. It limits approval to tablet behavior.'),
 'theme-04':('pass',['C5'],'Credits checklist preparation and week-one observation without turning 612 accepted events or 47 delayed uploads into whole-depot outcomes. Preserves non-random lanes, weak comparisons, ambiguous missing collection scans and the unavailable raw export.'),
 'theme-05':('pass',['C4'],'Names Contributor 07 as the source of operator feedback and the subject as the implementer of wording and shift-card changes. The claim keeps the later supervisor report bounded to two lanes and three shifts.'),
 'theme-06':('pass',['C7'],'The account distinguishes a proposed expansion from Operations’ training-capacity deferral and a continued two-lane trial. The claim identifies label defects as outside queue work. However, the model wrongly dismissed the supplier notice as irrelevant, and one supporting quotation changes source punctuation; both failures are reported separately.'),
 'theme-07':('pass',['C6'],'Names the person who found the cross-device problem, preserves the subject’s analysis and service dependency, and states that the banner remained unimplemented. Does not turn the service prototype or review of its response shape into the subject’s completed fix.'),
 'theme-08':('pass',['C8'],'Separates the subject’s runbook and continuing availability from Contributor 04’s routine maintenance after the handover. Does not attribute the later releases to the subject.'),
 'theme-09':('partial',['C9'],'Finds continued two-lane use, paper fallback and the non-causal 34/40 versus 38/41 comparison. It omits the replacement labels surviving eight wash cycles, despite reading that message in full. The claim and account also call the combined collection-or-open-exception measure merely figures; the exact endpoint is preserved only inside the quotation.'),
 'theme-10':('pass',['C9'],'Treats the July decision as approval for a future two-lane extension, not observed August use or a general launch. The claim preserves stable queue operation, replacement labels and trainer availability as joint reasons, with collection impact still uncertain.'),
 'theme-11':('pass',['C1'],'Finds and uses the January paper-process delay as a pre-existing condition. Leaves the facilities notice and lunch poll out of the contribution story. That appropriate filtering does not justify also dismissing the project’s supplier-failure notice.')
}
read_ids={r['id'] for r in read(folder/'result.json')['records']}
themes=[]
for t in gold['themes']:
    status,ids,assessment=judgements[t['id']]
    assert all(any(c['id']==id for c in review['claims']) for id in ids)
    themes.append(dict(t,status=status,claim_ids=ids,assessment=assessment,unread_anchors=[id for id in t['anchors'] if id not in read_ids]))
events=trace['events'];plan=trace['planning']
contexts={e['arguments']['id'] for e in events if e['tool']=='read_context' and e['result'].get('end_reached')}
sweeps={(e['arguments']['source'],e['arguments']['window']) for e in events if e['tool']=='list_roots' and e['result'].get('end_reached')}
quotes=sum(len(c['evidence']) for c in review['claims'])
quote_errors=[e for e in provenance['errors'] if 'quote missing or ambiguous' in e]
structure_errors=[e for e in provenance['errors'] if e not in quote_errors]
counts={'fully_met':sum(t['status']=='pass' for t in themes),'partial':sum(t['status']=='partial' for t in themes),'missed':sum(t['status']=='missed' for t in themes),'themes':len(themes),'full_records':len(read_ids),'snippet_only':len(trace['snippet_only_ids']),'source_calls':trace['source_calls'],'requests':trace['requests'],'cache_hits':trace['cache_hits'],'remaining_source_calls':plan['calls_remaining'],'completed_contexts':len(contexts),'completed_source_window_sweeps':len(sweeps),'exact_quotes':provenance['quote_count'],'submitted_quotes':quotes,'quotation_errors':len(quote_errors),'structural_flags':len(structure_errors),'disposition_records':provenance['disposition_records'],'attribution_chains':provenance['attribution_chains']}
assessment={
 'headline':'Earlier context survived. The stopping decision did not.',
 'summary':'The story now names who found problems, who corrected them and who owned later work. Repeated requests used the cache. But the researcher dismissed a relevant supplier notice and incorrectly said the budget forced it to stop.',
 'scope_limit':'One unchanged story from a separate AI author; one uncoached research attempt. Nine of eleven themes fully met and two partly met. This is not a clean pass: one quotation is not verbatim, and the frozen validator flags two attachment dispositions.',
 'expected_records':len(gold['expected_records']),'themes':themes,
 'issue_heading':'A completed queue can still hide unfinished research.',
 'issues':[
  {'severity':'Wrong relevance decision','claim_ids':['C7','C9'],'detail':'chat:010 reports adhesive failure, supplier replacement and manual entry for unreadable labels. The model grouped it with two unrelated notices and called it irrelevant based on its snippet. Four source reads remained. The queue tracks replies, references and pages; a snippet-only standalone record can fall outside those obligations.'},
  {'severity':'Incorrect stopping explanation','claim_ids':[],'detail':'The model says it stopped after 43 charged calls plus a status audit because of the 45-call budget. Receipts show 44 requests, three cache replays and only 41 charged calls. The last status response reports four remaining source calls. No budget limit forced the omission.'},
  {'severity':'Quotation failed','claim_ids':['C7'],'detail':'The model’s quotation ends “Keep lanes 2 and 4 running.” The source says “Keep lanes 2 and 4 running; we can revisit after the roster change.” Changing the semicolon to a period fails the exact-span check. The deferral interpretation remains supported, but the quotation cannot be presented as verbatim.'},
  {'severity':'Read context still compressed away','claim_ids':['C2','C9'],'detail':'The final claims omit the server uniqueness guard from the joint design discussion and the eight-wash-cycle replacement-label observation. Both were read. Grouping 33 records as used with one generic reason does not show that every material detail survived synthesis.'},
  {'severity':'Metric definition lost','claim_ids':['C9'],'detail':'38 of 41 versus 34 of 40 measures a recorded collection OR an open-customer exception by a seven-day review point. The exact source quote includes this definition, but the claim and narrative reduce it to figures. A reader could mistake it for a collection-success count.'},
  {'severity':'Evaluator boundary mismatch','claim_ids':['C5'],'detail':'The frozen structural validator accepts only primary record IDs in dispositions, so it flags the available template and unavailable export entries. Tool receipts show both attachments were explicitly checked. These two flags are an evaluator contract limitation, not invented attachment evidence. The original failed validation is retained rather than patched into a pass.'}
 ],
 'limitations':[
  'The revised source server, researcher prompt, schemas, evaluator checks and unit tests were frozen before authoring. The separate author produced 39 records and 11 themes; no content was edited. The researcher’s first response was preserved before the rubric was opened.',
  'Author and researcher used the same provider/default model family, with no exact identifier captured. This assistant graded the result manually. The new case repeats a warehouse-prototype pattern and reuses the fictional project name of an earlier, different case; separate invocation is weaker independence than a human-authored out-of-domain benchmark.',
  'The theme score measures interpreted coverage separately from quotation validity. Nine full and two partial is not an end-to-end pass: one of 33 quotations fails exact matching, and the stopping explanation contradicts the receipts.',
  '35 of 38 accessible primary records were read in full. Three were snippet-only: two distractors and a relevant label-failure notice. One further record lies beyond the horizon. The available attachment and explicit unavailable result are outside that primary-record denominator.',
  'Nine discovered contexts and all nine source/time-window sweeps completed. Earlier enumeration found the January pre-existing problem, but its 90-day boundary does not establish completeness across older history.',
  'Three duplicate requests replayed saved responses without a new source charge. This fixes repeat source work on immutable snapshots; it does not stop the model requesting duplicates or supply a production revision/expiry policy.',
  'The 45 charged-source-call limit, 60-request ceiling and parent-inclusive context responses differ from prior runs. Different stories and protocols prevent a controlled score comparison.',
  'The output includes seven contribution chains and dispositions covering all 35 fully read primary records. Those structural aids did not prevent omissions within records marked used or a mistaken relevance decision about an unread standalone record.',
  'No search call was made. The earlier sweep was exercised; broadening empty queries and finding context outside its 90-day window were not. The story has no multi-level reply chain, and only two irrelevant notices.',
  'No private archive or live platform was accessed. Synthetic source replay is offline and read-only; model inference used authenticated Codex. The earlier model responses, fixtures and freeze hashes remain unchanged.'
 ],
 'method':'A separate isolated AI author received the generic brief and schema only. A fresh researcher received scope and chose all 44 MCP requests, including three cache replays. This assistant then compared the preserved account with the hidden author rubric and original records. The frozen exact-quote and disposition validator was run once without changing it to accept this result.',
 'next_experiment':'Before another untouched case, make stopping reconcile the remaining budget and all surfaced standalone records, require explicit metric definitions in claim text, and distinguish attachment dispositions from primary records. Test outside warehouse prototypes with a separate assessor. Preserve this failed first result.',
 'summary_counts':counts,'final_planning':plan,'quotation_errors':quote_errors,'structural_flags':structure_errors,
 'adjudicator':'This assistant; manual original-source comparison against separate-author rubric',
 'substantive_attempts':1,'content_edited':False,'prompt_frozen':True,'private_records_supplied':False,
 'review_sha256':hashlib.sha256((folder/'researcher/response.json').read_bytes()).hexdigest(),
 'gold_sha256':hashlib.sha256((ROOT/'fixtures/attribution.gold.json').read_bytes()).hexdigest()
}
assert (counts['fully_met'],counts['partial'],counts['missed'])==(9,2,0)
assert counts['exact_quotes']==32 and quotes==33 and len(structure_errors)==2
(folder/'assessment.json').write_text(json.dumps(assessment,indent=2,ensure_ascii=False),encoding='utf-8')
# Preserve attachment availability as observed by the researcher, outside record coverage.
attachments=[]
for a in corpus['attachments']:
    seen=[e for e in events if e['tool']=='read_attachment' and e['arguments']['id']==a['id']]
    if seen:attachments.append(a|{'observed_result':seen[-1]['result'].get('reason','Full attachment returned'),'read_by_researcher':True})
(folder/'attachments.json').write_text(json.dumps(attachments,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(counts))
