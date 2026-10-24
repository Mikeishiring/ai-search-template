"""Strict post-run assessment. Never supplied to the researcher or used for a retry."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parent;folder=ROOT/'runs/depth'
read=lambda p:json.loads(p.read_text(encoding='utf-8'))
gold=read(ROOT/'fixtures/depth.gold.json');corpus=read(ROOT/'fixtures/depth.corpus.json')
review=read(folder/'researcher/review.json');trace=read(folder/'trace.json');provenance=read(folder/'provenance.json')
judgements={
 'theme-01':('partial',['c3','c6'],'Credits personal validation, inline messages and a regression test. The guarded form and logging appear as release features, but personal implementation of those parts is not carried through from repo:003. This is an incomplete contribution account, not false sole-ownership attribution.'),
 'theme-02':('pass',['c2'],'Preserves the six-case mapping, unresolved policy questions and deliberate escalation. Assay-rule authority remains with Contributor 03.'),
 'theme-03':('pass',['c3'],'Names Contributor 02 as the source of the late-warning feedback, Contributor 01 as the implementer of the earlier check and test, and Contributor 04 as the process-map owner. The reply-to-reply correction survives in the final narrative.'),
 'theme-04':('partial',['c4'],'Preserves personal diagnosis, release halt and three sandbox records with no publication. It omits completed cross-unit and server-side safeguards from repo:007, despite reading them, and does not clearly connect the original defect to the subject’s implementation or the shared review oversight. Claim c4 cites diagnosis but leaves the impact sentence unselected.'),
 'theme-05':('partial',['c5'],'Preserves four verified aliases and the ten unresolved labels with Contributor 05’s authority. Drops the subject’s dry-run migration, rollback verification and runbook, then omits the later resolution of all fourteen exceptions by several owners. Those details were read, not inaccessible.'),
 'theme-06':('partial',['c6'],'Correctly limits release to one pilot laboratory and requires a separate expansion decision. Omits the 24 May date and the functional approvals/application-readiness split recorded in chat:013. Product release is preserved; the responsibility chain through release is incomplete.'),
 'theme-07':('missed',[],'Reads the trial, first-shift and month-one records but excludes the usable counts entirely: 18 synthetic entries, six first-shift users, 126 logged entries, seven pre-submission blocks and zero breaches in only 40 audited releases. No production-reliability claim is invented, but caution becomes loss of the bounded evidence.'),
 'theme-08':('pass',['c7','c8'],'Preserves the supervisor approval failure, the subject’s two proposed responses, the policy owner’s narrower request, the implemented acknowledgement/display change and the reviewer’s warning that salience does not establish sound decisions. Does not claim mandatory rationale shipped.'),
 'theme-09':('missed',[],'Reads both expansion records but omits the instrument-interface dependency, the pilot-only status through the horizon and the unassessed third laboratory. The account mentions postponed expansion vaguely and calls the citation IDs unavailable; the saved MCP responses contain them.'),
 'theme-10':('partial',['c8'],'Retains uncertainty about future supervisor decisions and avoids incorporating unrelated records into the story. It does not explain the unaudited portion of the measurement, and replaces the known reason for delayed expansion with an unsupported citation-availability limitation. Four distractors remain unread and are correctly left unresolved rather than declared irrelevant.')
}
records=read(folder/'result.json')['records'];read_ids={r['id'] for r in records};themes=[]
for t in gold['themes']:
    status,ids,assessment=judgements[t['id']]
    assert all(any(c['id']==id for c in review['claims']) for id in ids)
    themes.append(dict(t,status=status,claim_ids=ids,assessment=assessment,unread_anchors=[id for id in t['anchors'] if id not in read_ids]))
events=trace['events'];plan=trace['planning'];receipt=trace['completion_receipt']
contexts={e['arguments']['id'] for e in events if e['tool']=='read_context' and e['result'].get('end_reached')}
sweeps={(e['arguments']['source'],e['arguments']['window']) for e in events if e['tool']=='list_roots' and e['result'].get('end_reached')}
# Compare claimed citation loss against the transport output actually retained by the CLI.
delivered={};sizes=[]
for item in read(folder/'researcher/events.json'):
    if item.get('type')!='mcp_tool_call':continue
    for block in item.get('result',{}).get('content',[]):
        if block.get('type')!='text':continue
        try:result=json.loads(block['text'])
        except ValueError:continue
        if result.get('citation_spans'):sizes.append(len(block['text']))
        for span in result.get('citation_spans',[]):delivered.setdefault(span['record_id'],[]).append(span['span_id'])
lost_ids=['repo:007','repo:008','docs:006','chat:015','chat:016','docs:009','chat:019','docs:010']
assert all(id in delivered for id in lost_ids)
branch_opportunities=[]
for previous,event in zip(events,events[1:]):
    queue=previous['result'].get('planning',{}).get('priority_branches',[])
    if queue and event.get('source_charge'):
        branch_opportunities.append({'sequence':event['sequence'],'recommended':queue[0]['arguments']['id'],'actual':event['arguments'].get('id'),'followed':event['tool']==queue[0]['tool'] and event['arguments']==queue[0]['arguments']})
counts={'fully_met':sum(t['status']=='pass' for t in themes),'partial':sum(t['status']=='partial' for t in themes),'missed':sum(t['status']=='missed' for t in themes),'themes':len(themes),'full_records':len(read_ids),'accessible_records':len(gold['expected_records']),'source_calls':trace['source_calls'],'requests':trace['requests'],'cache_hits':trace['cache_hits'],'remaining_source_calls':receipt['counts']['source_calls_remaining'],'remaining_requests':receipt['counts']['requests_remaining'],'completed_contexts':len(contexts),'unfinished_contexts':len(plan['unopened_contexts']),'completed_source_window_sweeps':len(sweeps),'unread_surfaced_records':len(plan['unread_surfaced_records']),'unchecked_attachments':len(plan['unchecked_attachments']),'exact_spans':provenance['quote_count'],'submitted_spans':sum(len(c['evidence']) for c in review['claims']),'completion_receipt_valid':provenance['completion_receipt_valid'],'validation_flags':len(provenance['errors']),'disposition_records':provenance['disposition_records'],'attribution_chains':provenance['attribution_chains'],'priority_opportunities':len(branch_opportunities),'immediate_priority_follows':sum(b['followed'] for b in branch_opportunities)}
assessment={
 'headline':'The replies were read. Too much was lost in the telling.',
 'summary':'Both nested correction threads reached the final account. Other contributions, usage figures and the reason expansion stalled were dropped, even though their source text and citation IDs were returned.',
 'scope_limit':'One untouched 48-record laboratory-tool story; one uncoached attempt. Strict completeness review: 3 of 10 themes fully met, 5 partial and 2 missed. All 30 quotations resolve exactly, but one record lacks an omission explanation. This is not an end-to-end pass.',
 'expected_records':len(gold['expected_records']),'themes':themes,
 'issue_heading':'Retrieval succeeded where synthesis still failed.',
 'issues':[
  {'severity':'Depth improved, priority only partly followed','claim_ids':['c3','c5'],'detail':'All 14 discovered contexts were completed, including two reply-to-reply corrections. They were read before standalone records. However, the model followed the highest-priority branch immediately in only 2 of 9 opportunities; the other seven calls opened different contexts without a specific explanation. This case has no chain as deep as the preceding test, so it does not prove the hardest depth failure is fixed.'},
  {'severity':'Available citations described as missing','claim_ids':['c4','c5'],'detail':'The recorded CLI responses contain span IDs for the completed unit fix, migration tooling, runbook, later exception resolution, measurement and expansion records. The model nevertheless says those IDs were unavailable. The exact internal cause is unobserved; context loss is a hypothesis. It made no cached recovery read, despite 33 request slots remaining at stop.'},
  {'severity':'Personal follow-through still omitted','claim_ids':['c4','c5'],'detail':'Diagnosis and the later approval-control correction survive. Completed unit-pair/server validation, rollback safeguards, the runbook and the subject’s support for resolved migration exceptions do not. An omission rationale saying a record is contextual does not justify discarding distinct contributions.'},
  {'severity':'Measured use and external dependency disappear','claim_ids':[],'detail':'The model reads the trial, six-user first shift, month-one sample and expansion tracker but excludes their substantive findings. It should preserve the bounded counts and the instrument-interface dependency, with their limits, instead of calling them source gaps.'},
  {'severity':'One evidence accounting failure remains','claim_ids':[],'detail':'chat:009 was read and appears in a rejected conclusion, but is neither quoted by a claim nor explained in uncited_records. The compiler marks it unresolved and retains the validation failure. Derived role links and used-record links are consistent. The contract excludes rejection-only references from quoted claim use: this is a remaining interface/contract failure, not proof that the record was never considered. No explanation was silently supplied.'},
  {'severity':'Discovery spends a large share of the budget','claim_ids':[],'detail':'Fifteen root-enumeration calls and one inventory call precede all full reads. At 45 charged calls, two relevant issue roots, four distractors and two attachments remain unread. The researcher then attempts one uncached read after exhaustion; the server rejects it without charging. A valid stopping receipt does not make the account complete.'}
 ],
 'limitations':[
  'The separate AI author saw a generic fictional brief and domain exclusions, not private records, the implementation, the researcher prompt or previous cases. It produced 48 records despite a requested 32–40. The predeclared structural acceptance range was 32–64; the story was accepted unchanged. The larger story competes for the same 45-call budget.',
  'Author and researcher used separate isolated sessions with the same provider/default model family. The exact model version was not captured. This is procedural independence, not a human-authored benchmark or an independent provider replication.',
  'This assistant applied the hidden author rubric only after the first response. Full credit requires the material details of the whole theme. Partial scores represent incomplete coverage, not necessarily false claims. The three full themes cover rule authority, collaborative workflow correction and the later approval-control response.',
  '41 of 47 accessible primary records were returned in full. One additional record is beyond the August horizon and was not supplied. All discovered contexts and all nine source/window sweeps completed; two relevant standalone roots and four distractors remained unread. No keyword searches were used.',
  'The deepest accessible records in this case are replies to replies. The preceding case had a deeper repository chain. This run exercises nested follow-up but cannot establish reliable traversal at arbitrary depth or scale.',
  'Thirty selected spans match exact original text. The compiler derives seven contribution chains and one disposition per full record. It still reports the missing semantic omission note for chat:009; no fabricated explanation was inserted.',
  'The claimed citation gaps are contradicted by the saved source and CLI tool responses. Those logs do not expose the model’s internal attention or any host-side context handling. Each full-read response is roughly 7,868–9,844 characters, much of it repeated planning inventory; reducing that burden is a plausible next experiment, not a proven diagnosis.',
  'The source budget ended at 45 with 47 requests and no cache replays. Cached reads were still permitted before the final receipt within the 80-request ceiling. The model did not use them to recover IDs. The accepted source-limit receipt certifies only that stopping state, not semantic completion.',
  'Neither attachment was checked. The audit export is an evaluator copy and the photographs are marked unavailable in the fixture; neither status was discovered by the researcher. The derived checked-attachment ledger is therefore empty.',
  'The source’s 126-entry count and statement about the other 86 released entries need definition reconciliation if used as a production metric: seven pre-submission blocks are also reported. The defensible reported observation is zero breaches among 40 audited releases, not a population error rate. The model omitted this evidence rather than resolving its definition.',
  'No protocol, prompt, schema or source fixture was changed after story generation; no substantive retry occurred. Scores across these different stories and protocols are not causal estimates of improvement. No private archive or live integration was accessed.'
 ],
 'method':'Protocol, prompts, schemas, compiler and tests were hash-frozen before a separate AI authored the story. A fresh researcher chose every MCP request and source span from scope alone. After its first response, this assistant compared the hidden rubric, original records, source receipts and recorded CLI responses. Mechanical validation and semantic completeness are reported separately; no coaching, fixture edits or retry.',
 'next_experiment':'Test a compact, persistent citation-and-contribution ledger with cache-only evidence recovery before finalisation. Avoid repeating the entire inventory on every read. Then use another untouched independent story to test whether the same bounded findings survive into the account; keep this failed first result unchanged.',
 'summary_counts':counts,'final_planning':plan,'completion_receipt':{k:v for k,v in receipt.items() if k!='planning'},'validation_errors':provenance['errors'],'priority_opportunities':branch_opportunities,'citation_delivery_audit':{id:delivered[id] for id in lost_ids},
 'adjudicator':'This assistant; strict manual comparison with separate-author rubric and original records','substantive_attempts':1,'content_edited':False,'prompt_frozen':True,'private_records_supplied':False,
 'raw_response_sha256':hashlib.sha256((folder/'researcher/response.json').read_bytes()).hexdigest(),'compiled_review_sha256':hashlib.sha256((folder/'researcher/review.json').read_bytes()).hexdigest(),'gold_sha256':hashlib.sha256((ROOT/'fixtures/depth.gold.json').read_bytes()).hexdigest()
}
assert (counts['fully_met'],counts['partial'],counts['missed'])==(3,5,2)
assert counts['exact_spans']==counts['submitted_spans']==30 and counts['completion_receipt_valid']
assert counts['validation_flags']==1 and counts['remaining_source_calls']==0
(folder/'assessment.json').write_text(json.dumps(assessment,indent=2,ensure_ascii=False),encoding='utf-8')
attachments=[a|{'read_by_researcher':False,'observed_result':'Evaluator copy; not checked during research.'} for a in corpus['attachments']]
(folder/'attachments.json').write_text(json.dumps(attachments,indent=2),encoding='utf-8')
print(json.dumps(counts))
