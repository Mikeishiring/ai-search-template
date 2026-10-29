# Compare a role with career evidence

Use this when a vacancy is supplied or the person wants to test how their context supports a search. Use the existing career document as the durable record. Keep the role-specific assessment distinct from supported facts; the vacancy does not change the person's history, goals or proficiency.

## Read the job before using its labels

Read the employer's full description and retain its URL and retrieval date. Search-service categories and extracted skills are navigation aids. Resolve conflicts in favour of the actual wording; if the full description is unavailable, qualify the comparison instead of treating a snippet as complete.

Separate the work to be done, experience explicitly required, helpful backgrounds, things the employer expects someone to learn, and practical conditions. A network someone will build is not necessarily a network they must already possess. A department containing “Staff” need not describe engineering seniority. Company technology is not automatically a candidate qualification.

Translate each material activity into evidence questions. For a referral programme, look for design, launch, use, maintenance and outcomes. For a technical search, look for target calibration, market mapping, attribution of expert input, outreach and what happened next. Use the person's vocabulary and adjacent-domain examples rather than searching only for the job's keywords.

## Retrieve before asking

Start with the canonical packet, including timeline sources absent from selected work accounts. The bundled helper searches work narratives, timeline entries and retained sources without changing them:

```text
python scripts/retrieve_context.py career-context.html --query referral --query leaderboard
python scripts/retrieve_context.py career-context.html --layer sources --query referral --offset 8
python scripts/retrieve_context.py career-context.html --read sources:source-id
```

Queries are literal, case-insensitive alternatives. Results are paginated separately for each layer, with matching fields and direct reference links. These are reading leads, not relevance scores or evidence judgments. Read full selected records, including limits; a hit in a question, proposal or contrary account is not proof of capability. Inspect the person, profile and collection inventory separately for stated goals and source boundaries.

Follow consequential gaps into already-authorized local exports or connectors named by the collection inventory. The portable packet is selected evidence, not the entire source archive. Search original documents, parent conversations, later outcomes and criticism; distinguish the person's contribution from other people's work. Record queries, sources read, coverage and remaining leads. Open databases read-only in place. Do not silently widen source permissions.

Before asking the person a factual question, identify what relevant available material has already been checked and why it cannot answer it. In a context test, an unresolved item can remain unknown; do not turn the exercise into an intake interview. Ask only when an answer is necessary for the requested decision. Missing access, a retrieval miss, insufficient evidence, a confirmed lack of experience and an unknown preference are different states.

## Judge each connection

Keep these distinctions visible where they change the conclusion:

- **Activity:** direct experience, transferable experience, or not established within the searched scope.
- **Domain:** the same field or a field whose methods may transfer. Technical recruitment does not by itself establish expertise in every research discipline.
- **State and ownership:** proposed, implemented, trialled, used, reused or measured; personal contribution and shared credit. Do not collapse these into one strength score.
- **Evidence and limits:** source IDs, originals versus recollections, later corrections and contrary evidence. Repeated imports are not independent corroboration. Interview participation counts do not establish sourcing success or quality of hire.
- **Conditions and motivation:** compare stated preferences with the role separately from capability. Do not infer willingness to commute or a scientific mission from project keywords.

Tool use, generated code, documentation links and co-author credits do not establish professional relationships with the tool's maker. Assisted implementation can be relevant without independent programming fluency. Preserve explicit self-assessment and assess the work actually required by the job.

Return a short evidence-backed comparison and the uncertainties that affect it. Prefer specific examples and consequential limits to a match percentage. Cite the employer for requirements and the career record for the person's work. Do not publish private source text or candidate identities.

## Carry useful evidence back

When working in a maintained career workspace, complete the evidence update in the same document during the comparison. Do not leave useful discoveries only in the response, a case file or a queue for the next session. An explicitly read-only or comparison-only request takes precedence.

- Reconcile each useful finding with existing work accounts and source IDs. Extend the matching account when it is the same episode; add a separate account when it gives a materially different example. Reuse retained sources and identify copied or re-read originals without multiplying apparent corroboration.
- Keep durable facts and consequential limitations: the person's actions, decisions, shared credit, assistance, actual state, later use and contrary evidence. Derive skills/tools from that work. Do not import job keywords, an inferred preference, a fit verdict or an unanswered requirement as a new career fact.
- Link supported dates into the existing timeline and link each period to its account. Leave undated evidence undated. Preserve meaningful earlier prose; replace a claim only when the new evidence corrects or qualifies it.
- Review dependent interview stories and answers against the changed evidence. Add a useful example when it expands the person's preparation; retain existing introductions, alternatives and rehearsal notes. Refresh the evidence fingerprint only after reconciling the preparation, never just to bypass freshness validation. Do not retarget the entire document to the vacancy unless requested.
- Keep new synthesis as draft and retain the person's prior corrections. Update source-coverage records to describe the actual additional reads. Use the established private HTML path and [local archive](local-archive.md) update so the earlier revision remains recoverable in the same database.
- Reopen the output and check that each new account, its sources, timeline links and preparation survive full export and reopening. Confirm the old accounts and notes remain. Mention what was carried back and any unresolved evidence without turning those gaps into an intake questionnaire.

If the maintained source is unavailable or has conflicting edits, preserve a bounded reconciliation record and identify the blocker; do not claim the main document was updated. A portable attachment without a writable maintained workspace can still support a comparison without inventing another canonical version.

## Learn from a test

Retain a private case record containing the role source/date, the context fingerprint used for the assessment, search scope, material evidence links, assessment and what changed after deeper retrieval. After carrying evidence back, record the resulting account/source IDs and revision separately from that historical assessment fingerprint. The case record documents the test; the complete career document remains the reading entry point.

Evaluate retrieval and interpretation separately. A controlled comparison can hold the queries fixed and compare the visible work index with the packet's full sources, then record what further archive reads add. It measures those queries against those records, not overall model accuracy. Check for both overlooked evidence and overstated matches. Reuse synthetic cases with different domains and assistance levels for software tests; reserve claims about judgment quality for observed model behaviour. A worked example is not an independent benchmark.
