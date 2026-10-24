# Local AI research MVP

This is the historical experiment notebook. For first-time setup or your own data, start with the [root README](../README.md). The separate personal workspace command does not use this experiment ledger or its synthetic MCP server.

This is a local research prototype with an authenticated Codex reviewer. All research records are synthetic. The source replay runs offline; the optional reviewer sends only its synthetic evidence packet to the Codex service. No private archive, live source connector or calendar is used. Model inference is remote, while the evidence, response and dashboard are saved locally.

Open `../AI-SEARCH-MVP.html` for the results and original synthetic passages. The code runs with Python 3.11 or later and the standard library.

The experiment views share a context reader. Select a theme to inspect its assessment, model claims and quotations; AI views start with a partly met theme. Source visits have a return action that restores your filters, and selections persist while switching cases. Narrow layouts use a native theme selector. The report is generated from `report-template.html` and `report-style.css` into one self-contained file.

The design pass has passing state, evidence-preservation and contrast checks. Rendered inspection remains blocked by the local-file browser policy; layout, actual keyboard/touch behaviour and hover playback are not visually verified. The receipt is `runs/design/verification.json`.

## Run and resume

```sh
python cli.py run training
python cli.py evaluate training
python cli.py run challenge --steps 5
python cli.py run challenge
python cli.py evaluate challenge
python cli.py run search_only
python cli.py run semantic
python -m unittest discover -s tests -v
python cli.py report
```

Run commands from this directory. Re-running resumes the same database. `--steps` sets a bounded operation budget. `--refresh` deliberately re-reads sources and preserves earlier record revisions. The report is generated from saved results; opening it does not run the research.

The CLI accepts only the bundled fixture names. Runtime audit hooks reject private workspace file reads, evaluator answer keys, network calls and subprocesses during research. This is defence in depth, not an OS sandbox. Small local SQLite databases contain synthetic records only. Tests reuse one small scratch database.

## What works

- Separate coverage and follow-up queues, automatic source-link traversal and missing-stage searches.
- Paginated roots, older roots active in the window, later replies through a follow-up horizon, nested blocks and original attachment status.
- Immutable source revisions, exact quoted spans, explicit connection groups, copied-record relationships and local operation receipts.
- Bounded interruption, expired-cursor recovery and idempotent replay.
- Honest search-only coverage and an unavailable attachment kept as a blocked task.
- A local stdio MCP bridge for an AI host, with anchored review submission.

## What the tests actually establish

The development fixture has 24 expected accessible records and 10 author-defined context themes. The runner retrieved all 24 and surfaced lexical signals for all 10; the single-query baseline surfaced 1.

The wording challenge has 20 expected records and 10 themes. The unchanged runner retrieved all 20 but surfaced only 5 themes; the baseline surfaced none. It missed self-initiation, the reduced mandate, later use, paused expansion and competing responsibilities in less literal language. The reviewer source hash was frozen before generating this challenge and is checked by a test.

This is program-blind, not independently blind: the research process cannot read the answer keys, but the same author designed the fixtures and implementation. The challenge intentionally stresses wording. Neither result estimates real-world accuracy. The baseline is deliberately shallow, not a competitive search system.

Infrastructure tests and semantic success are reported separately. A rule match is candidate evidence. The new model experiment below adds an interpretation layer; it does not establish autonomous research quality.

## First model experiment

The new Folio story concerns a museum caption tool. Its 22 accessible records include a corrected authorship claim, two reported uses, copied feedback, an unperformed trial, competing duties and a pause in expansion. The prompt and schema were frozen before story generation. The answer key and rule findings were excluded from the reviewer packet.

One substantive Codex response produced 13 claims and 17 quotations. All quotations matched exact source spans. Manual comparison against the pre-recorded rubric found 11 of 12 themes fully met and one partly met. The model kept implementation, fault, correction and approval responsibilities separate; rejected unsupported savings; and connected delayed teaching to its later completion.

The partial result matters. A staffing explanation for pausing expansion does not prove that performance or tool quality played no part. The answer also described local use as continuing when the latest record was an instruction to continue. Both qualifications remain visible beside the unedited response.

This is one author-designed case, graded by the same assistant that wrote the story. It is not an independent blind benchmark. The reviewer received the entire retained packet, so this tests interpretation rather than model-directed follow-up research. Exact quotations establish provenance, not sound reasoning or the truth of a source author's report.

The first output is preserved under `runs/semantic/model/`. Do not tune the prompt against it. To reproduce validation without a new model call:

```sh
python semantic_review.py
python assess_semantic.py
python cli.py report
node tests/check_report.cjs
```

`model_backend.py review` is the actual model entry point. It requires the installed Windows Codex CLI and an existing authenticated account. It refuses to overwrite the first response. `model_backend.py smoke` tests an empty packet and likewise preserves its first output. The backend uses the CLI default model; the precise model identifier was not captured, which limits reproducibility.

The backend disables user configuration, project instructions, discovered skills, shell, browser, apps, plugins, memory and multi-agent tools. It runs ephemerally with a read-only sandbox and rejects unexpected tool events. The review receipt recorded zero tool events. Only fixed synthetic inputs are accepted by the command; field and locator checks provide additional safeguards, not a general private-data classifier. See the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

An initial empty connection test timed out. Timeout reporting and the empty-test timeout were then adjusted; the prompt, schema, model options and story were unchanged. The subsequent empty test succeeded, followed by the single substantive review. Transport retries are not counted as semantic attempts.

## Separate-author autonomous experiment

An isolated Codex author wrote Project Lantern: 42 fictional records about a supervised refrigeration pilot. It received only a generic authoring brief and schema, with no earlier fixtures, implementation, research prompt or private history. The original output is preserved. It exceeded the requested 32–40 records; that size deviation was accepted without trimming the story or changing the researcher's 45-call budget. The original installer rejection and separate structural acceptance are documented in `story-freeze.json` and `accept_author_story.py`.

The source tools, research prompt, schema, page size and budget were frozen before authoring in `runs/autonomous/preregistration.json`. A fresh researcher received only the question and scope. It made 45 calls through a real local stdio MCP: six searches, eight root-list pages, 17 individual record reads, 12 context reads, inventory and status. No automatic crawler gathered its evidence and no follow-up hints were sent. The tools simulate chat, documents and repository data; they do not connect to real accounts.

The first answer read 31 of 41 accessible records, saw five more as snippets, and never surfaced five. It produced 15 claims with 27 exact quotations, all from records it actually read. Manual assessment against the separate author's hidden rubric found nine themes fully met and three partly met. It preserved shared ownership, defects and corrections, supervised operation, and the difference between an observed 38 kW difference and a controlled saving.

The omissions were material. It read the first trial-night message but never expanded the thread containing the 11-to-3 overlap count and a later selected-night use report. It left the second-site trial limitation and phase-two conditions in snippet-only records. It did not find the new horizon-summary document. Root enumeration covers the original question window; broader search and pagination were needed to find that later root. One initial search continuation also remained open.

The dashboard distinguishes evaluator copies from researcher reads. Post-run probes confirmed where the omissions could be found; those probes were recorded separately and never supplied back to the model. The broader document search required four pages, not one. Do not count this oracle-assisted audit as another successful research attempt.

Independence is limited: author and researcher were separate invocations using the same provider/default model family, not an independently recruited human author. This assistant graded the answer manually. The precise model identifier was not captured. The rubric is explicit and the story has little irrelevant material. These results are one failure case for follow-up planning, not an accuracy estimate.

To validate the saved autonomous run without another model call:

```sh
python prepare_autonomous_result.py
python assess_autonomous.py
python cli.py report
node tests/check_report.cjs
```

`independent_experiment.py research` is the authenticated model entry point and refuses to replace the first attempt. `autonomous_server.py` exposes only fixed synthetic sources through `source_inventory`, `search`, `list_roots`, `read_record`, `read_context`, `read_attachment` and `research_status`. Searches return snippets; full reads are accounted separately. Its file guard permits only the two fixed source files and the local receipt journal, blocks the answer key and arbitrary file reads, and denies networking and subprocesses. Query-scoped cursors and a durable 45-call limit prevent silent traversal outside the declared test. The MCP configuration follows the [Codex configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

The failed size check and a post-run audit-report counting bug did not alter the author output, researcher prompt, source server or research attempt. Their frozen hashes still match. The analyst's initial audit query had to be paginated to locate the horizon summary; that correction is reflected in the report rather than presented as a one-call discovery.

## Revised follow-up planner: first uncoached run

The stable dashboard now opens on **Follow-ups**, with **Earlier run** preserving the original failure. The revised source server adds an observed-evidence queue for reply flags, linked records, attachments and continuation cursors. Every full read includes child metadata. Root enumeration has separate primary and follow-up windows. The revised prompt reserves attention for later use and unresolved evidence; the model still chooses every call. The queue uses returned metadata and text only, never the answer key or unseen content.

Before authoring, the implementation, prompt, schemas, tests and 45-call budget were hashed in `runs/followup/preregistration.json`. A separate isolated Codex invocation wrote Harborlight: 38 synthetic records and 11 rubric themes. Its output was accepted unchanged. A fresh researcher received only scope and the synthetic MCP, then made one 45-call attempt. No human hints, fixture edits or model reruns occurred.

The researcher read **33 of 37 accessible records**, completed **11 discovered contexts** and **all six source/window sweeps**, and found both continued use in a later reply and the newly created horizon document. The assessment found **9 themes fully met, 1 partial and 1 missed**. All **30 quotations** match full records it actually read.

The remaining failures are material:

- It read the forklift-safety feedback and the subject's admission of a distance-only model, but left that attribution and mistake out of its account.
- It never discovered an unlinked pre-project export complaint, and left the linked baseline document unread.
- Its final three calls re-read records already returned in full, while one reference and one attachment remained unchecked.
- It made no search calls, so the revised query-broadening guidance was not tested. This case also lacks multi-level reply chains and contains only one irrelevant notice.

The pilot numbers remain reported figures. The available attachment is a descriptive placeholder, not raw shift rows that would permit recomputation. Completing this fixture cannot establish analytics verification.

This is a different story and rubric from the earlier run, so the score difference cannot establish a causal improvement. Author and researcher used the same provider/default model family; this assistant performed the manual assessment. The exact model identifier was not captured. These are inspectable cases, not a reliability estimate.

Local reproduction without inference:

```sh
python prepare_followup_result.py
python assess_followup.py
python cli.py report
node tests/check_report.cjs
```

`followup_experiment.py research` is the separate authenticated model entry point; it refuses to overwrite the first attempt. `followup_server.py` extends the frozen baseline source implementation without modifying it. Full raw responses, tool receipts, final queue, hidden rubric, assessment and quotation anchors remain under `runs/followup/` and `fixtures/followup.*.json`. The fixture is immutable; evaluator-only source copies in the dashboard were added after the researcher finished.

## Earlier context and attribution experiment

The `attribution` case preserves another independently authored story and the first research response. Its protocol is frozen in `runs/attribution/preregistration.json`; prior cases are unchanged.

- `attribution_server.py` replays already-read full records and exact repeated pages from saved responses. Replays spend no source budget, but every request is logged and the hard request ceiling is 60. The charged source limit remains 45. This cache is valid for this immutable synthetic snapshot; it is not a production freshness or revision strategy.
- Thread expansion returns an unread parent with its child page. Known child flags, references and pending pages remain explicit. This changes response efficiency as well as the prompt.
- Each source gains a 90-day earlier-activity sweep. Earlier searches can reach farther back; linked older records remain readable. A bounded sweep cannot establish completeness across an entire career or company archive.
- The research output includes contribution chains and dispositions for every fully read record. `attribution_review.py` checks that sources and claims resolve and quotations exist. It cannot determine whether a role is assigned correctly or a contextual disposition conceals a material omission. That still requires reading the final account against the original sources.

The first run read **35 of 38 accessible primary records**, completed **nine discovered contexts** and **nine source/window sweeps**, and used **41 charged calls across 44 requests**. Three duplicate reads were served from cache. It recovered the pre-project paper-process problem and named reviewers, operator-feedback sources, implementers and later owners in the final account. Manual grading found **9 of 11 themes fully met, 2 partial**.

This is **not a clean pass**. It dismissed a relevant label-supplier notice from a snippet, then falsely said the budget forced it to stop even though four charged reads remained. It omitted the specific server uniqueness guard and the eight-wash-cycle replacement-label observation from the final claims. The combined collection-or-open-exception metric lost its definition in the narrative. Of 33 submitted quotations, 32 match exactly; one replaces a semicolon with a period. The dashboard marks the altered quotation and retains the unedited model response.

The frozen validator also rejects two attachment dispositions because it knows only primary-record IDs. The receipts show both files were checked, including an explicit unavailable result for the export. Those two flags are an evaluator contract limitation, not fabricated attachment evidence. The validator was not changed to turn the experiment into a pass. Contribution-chain and record-disposition coverage are structural checks, not proof of semantic completeness.

The separately generated story reused a fictional project name from an older case and resembles the previous warehouse-prototype domain. It received no prior fixture or conversation, but same-provider synthetic authorship offers limited diversity. No search call occurred, so earlier keyword discovery outside the bounded sweep remains untested.

The separate author gets the same generic synthetic brief and no previous story, implementation or research prompt. Research begins only after the unchanged story is installed. The researcher sees scope and its chosen MCP results, never the rubric. Model inputs contain no private records. Inference uses authenticated Codex; the source server remains offline and read-only.

To validate saved results without another model call:

```sh
python prepare_attribution_result.py
python assess_attribution.py
python cli.py report
node tests/check_report.cjs
```

The authenticated entry point `attribution_experiment.py research` refuses to overwrite the first attempt. Source replays, changed parent inclusion and a different story make this a new protocol case, not a controlled score comparison with the earlier runs.

## Completion and immutable citations: first test

The dashboard now opens on **Completion**. This version retains every surfaced primary record as an unread obligation until it is read in full; the model can then judge relevance. `finish_check` is a free local audit that refuses a completion receipt while known work remains and source/request budget is available. It can instead accept a bounded incomplete stop at the real limit, preserving the unresolved list. The researcher must include the final receipt ID. This is observed-coverage accounting, not a semantic or archive-completeness certificate.

The model now selects `record_id` and immutable `span_id` rather than typing quoted text. `completion_review.py` resolves each selected span from full records returned to the model, preserving punctuation, offsets and identity. Unknown or mismatched spans fail. Quotations in the HTML are compiled source text; the account, claim wording and first raw response remain unchanged. Relevant-looking exact quotations can still fail to support the associated claim.

Before authoring, the server, prompt, schemas, compiler and tests were frozen. A separate author received the generic brief plus a domain-diversity constraint, three distractors and a material nested reply. It produced an unchanged 40-record museum-audio story with 12 rubric themes. The researcher then made one uncoached attempt.

Results: **38 of 39 accessible primary records read; 45 charged source calls; 47 requests; 43 selected quotations resolved exactly**. The final receipt correctly says `source_limit`, with zero source calls remaining, one unopened nested review context and one unchecked export attachment. Every surfaced standalone record—including all three distractors—was read before relevance was judged. No early finish check was attempted in the model run; refusal is covered by unit tests.

Manual assessment found **10 themes fully met and 2 partly met**. The research still missed a deep approval reply and omitted the subject's personal investigation of recording D from its final claims despite reading that evidence. The explicit limits were better than a false completeness claim, but the result is not exhaustive.

Four structural checks also failed and remain preserved: records marked used without linked quotations; one record listed twice because its child was unresolved; a role source outside the chain's linked claims; and an unchecked attachment included in the checked-attachment ledger. All 43 source-span resolutions and the completion receipt passed. The overall result is therefore **not an end-to-end pass**. Nothing was rewritten or rerun to obtain a higher score.

The read-every-surfaced-record policy is deliberately conservative for a small bounded test. It trades relevance filtering errors for source-call cost: 14 enumeration calls and three distractor reads compete with deeper follow-ups. Future work should test allocation across those leads, derive record/chain cross-references mechanically, and separately assess whether personal diagnostic work survives synthesis. A different domain, citation protocol, free audit accounting and 80-request ceiling mean this is not a controlled comparison with earlier scores.

```sh
python prepare_completion_result.py
python assess_completion.py
python cli.py report
node tests/check_report.cjs
```

These commands validate and render the saved case without inference. `completion_experiment.py research` is the authenticated entry point and refuses to replace the first attempt. Raw span selections are in `runs/completion/researcher/response.json`; the compiled source-quotation view is `researcher/review.json`. `calls.jsonl` preserves all receipts. Source files, hidden rubric, manual assessment and frozen hashes remain separate. Private records and live integrations were not accessed.

## Deep-thread and derived-evidence experiment

The newest **Deep threads** view preserves one first run on Project Glassfin, a synthetic laboratory entry-form project. The author wrote 48 records after the implementation and prompts were frozen. That exceeds the requested 32–40 but lies within the preregistered acceptance range of 32–64; nothing was trimmed or rewritten. A separate researcher received only scope and read-only synthetic MCP access.

Changes: `depth_server.py` recommends the deepest observed open branch and supplies a subject-authored full-read index. `depth.schema.json` attaches roles to the evidence inside each claim. `depth_review.py` derives role links, quoted-record usage and checked-attachment status from citations and receipts; the AI explains uncited records. Attribution remains a semantic judgment. These files and their dependencies were frozen before the story existed.

Result: **41 of 47 accessible records read; 14 of 14 discovered contexts completed; 3 of 10 themes complete, 5 partial, 2 missed.** Both reply-to-reply corrections survived. The model followed the top branch immediately in only 2 of 9 opportunities, so prioritisation is still advisory rather than reliable. All 30 selected spans resolve exactly. One output-contract failure remains: chat:009 appears in a rejected conclusion but lacks the required uncited-record explanation. The compiler preserves that failure and marks the record unresolved.

The more serious failure is evidence retention. The model omitted completed testing and migration work, bounded usage figures and the external reason expansion stalled. It said their span IDs were unavailable, although the saved CLI responses contain them. The internal cause is not observable. Repeated 8–10 KB planning responses are one plausible burden, not a proven diagnosis. Free cached reads could have recovered IDs before the final receipt; the researcher used none and had 33 request slots remaining. No retry, hints or fixture-specific repair followed.

The rubric is graded strictly by this assistant after research. Partial means material details were omitted, not necessarily that a claim was false. This story is larger and its deepest chain is shallower than the preceding case, so score differences cannot establish causal improvement. Both attachments, four distractors and two relevant issue roots remain unread. No private records or live integrations were accessed.

```sh
python prepare_depth_result.py
python assess_depth.py
python cli.py report
node tests/check_report.cjs
```

These commands compile and audit the saved first response without inference. `depth_experiment.py research` refuses to replace it. The source log, raw response, compiled view, citation-delivery audit, hidden rubric and frozen hashes remain in `runs/depth`. The next experiment should test a compact persistent evidence ledger and cache-only recovery before finalisation on another untouched story.

## Evidence retention experiment

The newest **Evidence memory** view uses an untouched 42-record publishing-operations story. A separate AI wrote it after the new protocol was frozen. The first researcher attempt read **41 of 41 accessible records**, completed 17 discovered contexts and saved 41 record judgments. One post-horizon record stayed excluded. The strict source review found **10 of 11 themes complete and one partial**; all **80 selected spans** matched exactly.

`retention_server.py` adds cache-only `writing_packet` recovery and `save_notes` journal entries. These remain available after the 45-source-call budget is exhausted, within the same 80-request ceiling. Routine responses stop repeating the full read/author inventories. The researcher used nine writing packets and nine note batches after its source reads; it did not save interpretive notes incrementally as requested. The original source journal was persistent throughout.

`retention_review.py` assembles the account from every ordered claim sentence and its limits. It derives record and role links and reconciles rejection-only references. No independent summary can silently drop a selected claim. This changes the writing interface; it is not evidence that unconstrained summarisation became reliable. The AI still decides what to retain, how to describe it and whether an exclusion is justified.

The run remains a failure under strict end-to-end validation:

- Evaluation-report authorship disappeared from the saved notes and final role map, although the bounded figures survived.
- One role says a contributor provided pilot data, while the source only says they could add it. The narrative retains the unresolved external dependency correctly.
- `docs:010` is both cited and listed in `omitted_material`. Its explanation concerns content covered elsewhere, but that field excludes whole records. The validator preserves the contradiction; the record is not missing.

The original rejection-only accounting bug passes regression tests, including rejection of invented sources. This fresh story had no rejection-only record, so the particular path was not exercised by its AI run. The one audit attachment was never requested; its parent reports it unavailable. The dashboard separates that report from a tool-confirmed attachment result.

There were 65 total requests, including 20 local writing/audit operations, and 15 unused request slots at stop. The CLI reported 1,451,089 input tokens including 1,370,496 cached, plus 8,720 output tokens. This is not a cost estimate or evidence of greater efficiency. The separate author and researcher used the same default model family, with no exact model identifier captured. The story exceeds the requested 32–40 records but was accepted unchanged within the predeclared 32–64 range. No private data, prior conversation or live source access entered either session.

```sh
python prepare_retention_result.py
python assess_retention.py
python cli.py report
node tests/check_report.cjs
```

Those commands inspect and compile the saved output without inference. `retention_experiment.py research` refuses to overwrite the first attempt. The frozen hashes, source journal, note entries, raw output, compiled account and hidden-rubric assessment remain under `runs/retention`. No prompt, fixture, schema or compiler changed after generation, and no retest was used to improve the score.

## Ownership and action-state experiment

The default **Ownership** view contains a new, independently authored 40-record venue-ticketing story. The substantive researcher run read **39 of 39 accessible records**, saved 39 judgments and selected **70 exact spans**. The manual source review rated **11 of 12 rubric themes complete and one partial**. Structural validation passes; semantic gaps keep this from being an end-to-end pass.

`ownership_server.py` saves actor, action and state alongside exact evidence. Final roles reference those saved assertions. `ownership_review.py` derives evaluation-source credit from original author metadata and distinguishes it from implementation or measurement ownership. A single `coverage_notes` field can explain partial content or a whole-record exclusion; code determines whether a record is actually omitted. `draft_check` checks the complete draft before sealing, and final content must match that checked draft except for its receipt.

The new run preserves six evaluation-source authors and keeps the initial ownership offer distinct from assigned scope and later implementation. The firmware offer likewise remains an offer, with later completion supported by a separate record. The first draft check caught an unaccounted-for go/no-go record. The AI added an exclusion explanation and passed its second check without coaching.

The source audit still found meaningful losses:

- The receipt-order reviewer disappears from the account; the overlapping-batch reviewer becomes an unnamed reviewer. Both contributions were present in the notes, then excluded as already covered by the outcome.
- One sentence says the subject capped claims at two hours. Its actor event remains planned. A later source confirms an operational fallback under another contributor, but the final claim does not cite that link or establish personal completion.
- Ambiguity-aware sample payloads survive in a note and quotation, but disappear from the account and role description.
- One claim compresses an initial implementation and later correction into a misleading sequence.

Twenty-nine material records are cited; seven have explicit exclusions. All three distractors are excluded. No coverage note in this story refers to an already-cited record, so the cited-but-omitted repair has regression-test coverage rather than a live triggering example here. No rejection-only record occurs either. The available runbook diagram was requested after source exhaustion and refused; the unavailable metrics workbook was never requested. Neither was read.

There were **two research launches but only one substantive research run**. The first exposed no synthetic tools, read no records and made two empty host resource-list calls outside the allowlist. Its output remains excluded in `runs/ownership/researcher-transport-failure`. Connection-only diagnostics found a tool-list timeout, then successfully exposed source inventory. The unchanged runner, prompt, schema, compiler and story were restarted once. `transport-recovery.json` discloses this exception to the no-retry plan. No story record or hidden rubric was inspected before the substantive run; no second answer was selected for quality.

The substantive run used 45 source calls and 67 total requests. It recovered notes in eight writing packets and eight batches after source exhaustion, rather than incrementally. The source journal, raw response, both draft checks, notes, compiler output, hidden rubric and assessment remain local. Author and researcher used separate isolated invocations of the same provider/default family; their research receipts do not capture the exact model identifier. No private records entered either invocation.

```sh
python prepare_ownership_result.py
python assess_ownership.py
python cli.py report
node tests/check_report.cjs
```

These commands compile and inspect saved evidence without inference. The frozen research runner refuses to overwrite its response. Next, test whether the writer preserves each distinct contributor and action when excluding a source as redundant, and whether every completion verb is supported by a dated completion record. Preserve this result rather than rewriting it to pass.

## Use the MCP bridge

An MCP-capable AI host can launch:

```sh
python mcp_server.py
```

Configure the host with its absolute Python executable as `command` and the absolute path to `mcp_server.py` as its single argument. No host configuration was changed by this build. The server uses newline-delimited JSON-RPC over stdio and declares protocol revision `2025-06-18`. It has a stdio smoke test, not full MCP conformance certification. [MCP stdio transport](https://modelcontextprotocol.io/specification/2025-06-18/basic/transports), [lifecycle](https://modelcontextprotocol.io/specification/2025-06-18/basic/lifecycle).

Tools: `research_run`, `research_status`, `source_inventory`, `source_read`, `source_context`, `review_submit`. The first and last write only local synthetic state; source operations are read-only. There is no tool for arbitrary filesystem reads, shell execution or remote mutations.

The AI host supplies the language model. The local server does not contain one. For each claim, `review_submit` requires a nonempty claim, explicit limits, and exact evidence spans with current revision hashes. It rejects invented quotations and stale source revisions. It saves valid submissions as `needs_review`, with `meaning_checked: false`; correct citations do not prove a claim is true. General MCP submissions are saved separately. The packet-based Codex experiment has its own provenance check, manual assessment and dashboard section; it did not exercise model-selected MCP calls.

Use `RESEARCH-PROMPT.md` in a host connected to this synthetic server. Do not supply the evaluator's answer keys. A new independently authored fixture is required before treating the next model test as blind.

## Honest limitations and next work

1. The latest case preserves evaluation authors, saved action states and structurally consistent coverage, but exclusions still discard review contributions and prose can outrun its saved action state. Next, audit distinct contributions and dated completion evidence across notes, exclusions and final sentences. Keep every saved response unchanged.
2. Extend semantic evaluation beyond one manually graded story. The older training/challenge scores remain lexical signal recall, not semantic precision; do not compare them directly with the new rubric score.
3. Test independently authored data with more distractors and a separate assessor. Do not keep adding synonyms or prompts to pass existing stories.
4. Improve the question planner. Current missing-stage searches use broad terms and can repeat shallow hits; they do not formulate causal hypotheses.
5. Add actual Slack/Notion/GitHub adapters and contract tests only after the offline loop is reliable. Current platform names describe simulated data shapes.
6. Add transport retry/backoff, deletion/tombstone handling, incremental source change detection, attachment parsing, metric-event reconciliation and robust entity resolution. Those spec requirements are not implemented here.
7. Capture the precise model version and repeat evaluation across independent stories before estimating reliability. The dashboard exposes saved claims and criticism; it is not a live model chat.

The local-file browser policy blocked rendered inspection in this session. HTML generation, payload boundaries and script syntax can be checked locally; responsive layout and browser interaction need a permitted preview before calling the UI verified.

## Files and reproducibility

`engine.py` owns the ledger and scheduling. `adapter.py` supplies the synthetic read contract. `reviewer.py` contains the frozen lexical rules. Evaluator scripts `evaluate.py` and `assess_semantic.py` open answer keys; the researcher and model backend do not. `mcp_server.py` exposes the bounded bridge. `boundary.py` adds runtime guards. `model_backend.py` connects the reviewer, and `semantic_review.py` checks source anchors. `report.py` produces the single HTML entry point.

`fixtures/*.corpus.json` and `*.scope.json` are researcher inputs. `*.gold.json` is evaluator-only. Generator scripts are authoring tools and are not imported by the runner. Saved results, receipts and evaluations live under `runs/`.
