# Keep the evidence before choosing the story

Reading every source can still produce a thin account. A researcher can discard an important correction as context, copy a document heading instead of retaining its later events, or select a broad plan over a concrete contribution. More searches do not repair evidence already lost in notes.

New research workspaces therefore enforce a separate retention step:

1. `extraction_packet` returns sections of already-read originals with exact citation spans. `save_extraction` records events or a specific explanation of context for every section. Events retain actor, action, state, event date or uncertainty, significance and evidence. Each original is classified as work, discussion or evaluation, retaining report-author credit. Later substantive sections can correct a provisional classification made from metadata alone. The host derives durable record notes only after every section has a disposition. Empty originals receive an explicit contextual or irrelevant disposition with no invented spans or actions.
2. `episode_packet` recovers the events, including ones that might not fit the eventual narrative. `episode_inventory` assigns every event to a selected or reserve episode, or records a specific exclusion. Selected episode IDs become the sheet's account IDs.
3. After the first sheet plan, the researcher revisits the strongest reserve episode and compares it with an account that was selected. Changes to extracted evidence invalidate the selection. New evidence still requires fresh ownership and depth checks.
4. Completion and building refuse missing sections, an outdated inventory or an unchallenged selection. A model cannot bypass extraction by writing a generic record note.

Large archives can review material actor/actions in batches of 100 through `attribution_packet` and `save_attribution_coverage`. Each judgment still needs a claim carrying that exact saved role or an explicit omission reason. The final depth review combines current saved batches with any inline coverage and checks every attribution, including archives exceeding the 1,000-row inline limit. Duplicate inline/saved rows are rejected. Revised batches preserve earlier journal entries and invalidate an affected depth review. Changes to evidence, prose, layout or episode selection require fresh coverage for the new version.

Episode selection also supports bounded saves. `episode_assignment_packet` recovers the next 30 unassigned events; `save_episode_assignments` stores up to 100 explicit episode choices or specific exclusions. After every event is assigned, `episode_inventory` with `assignment_mode: "saved"` accepts episode definitions and the reserve comparison without repeating all event IDs. It rejects missing events, mixed inline assignments, unknown episode IDs and empty episodes. Changed extraction invalidates the assignments; changed assignments invalidate the selection and its depth review. Event pages return a compact selection summary. These operations reuse cached evidence and remain subject to the total request limit.

The checks reject repeated findings, copied-header placeholders, vague participation notes, foreign citation spans and blanket exclusion reasons. They do **not** prove that an interpretation is true or that every important event was recognised. An evidence-specific but incorrect note can still pass structural validation; semantic review and the person's corrections remain necessary.

The source boundary stays the same. These tools only recover records already fully read under the selected policy. They make no network requests and do not grant access to DMs or linked sources. Revoking the policy also blocks cached extraction. The journal preserves events and unused episodes locally, so later work can recover them without reconstructing the whole narrative.

Sections group complete citation spans with a target of 1,800 characters. A single long sentence remains intact, even when it exceeds that target; it is never silently truncated. Event dates must come from the source, not an assumed capture date.

Existing saved runs remain reproducible as legacy runs without this requirement. New sessions carry `career-retention/v1`; their build receipts state the protocol. No legacy result is relabelled as having passed it.

## Fictional regression case

The `story-depth` case contains a tempting strategy document, a personal handoff late in meeting minutes, a tool rename, a reported access problem and correction, shared implementation, practical teaching and later use. One direct message is explicitly excluded. The researcher receives the records and a general work question, not an expected story list.

```sh
python tools/run_research_demo.py ../story.html --workspace ../story-research --case story-depth
```

This invokes authenticated Codex with bundled fictional inputs only. The first result, journal and receipt are preserved. Evaluate the final account against the originals: origins and shared credit, correction, late handoff, alias-linked later use, training contribution and unresolved scope. Tool counts are not a quality score.

### Observed run, 26 October 2026

One corrected run finished in 205 seconds with no human follow-up. Its local receipt recorded 52 model tool calls and no unexpected tools; the source journal recorded 51 requests, including 36 charged source calls. The model used the CLI default, whose identifier was not exposed by the event stream. This is one small fictional case, not evidence of reliable performance on a large personal archive.

The saved journal retained 27 events from all 10 sections of nine authorised originals. The final sheet contained two accounts and 29 exact source excerpts. A separate read-only review compared the claims and embedded sheet data with the fictional originals:

| Evidence challenge | Observed result |
|---|---|
| Origin and shared credit | Retained Contributor 02's proposal and policy authority, Contributor 01's workflow implementation and Contributor 03's adapter work. |
| Error and repair | Connected the stopped trial, branch-scope error, narrower implementation and review; did not claim a full security audit. |
| Late evidence and rename | Recovered the handoff late in the minutes and connected Shelf helper to Beacon's later use. |
| Teaching and follow-through | Retained the illustrated guide, another contributor's examples, independent reuse and a later correction. |
| Tempting broad claim | Rejected delivery of the committee strategy; retained the afternoon-shift limit and unresolved freshness notice. |
| Excluded direct message | Neither read nor cited; the subject's personal motivation remained unknown. |

The result still repeated prose across sheet fields. One sentence interpreted the source's ambiguous “we tested” as the two named collaborators testing together; a reviewer should preserve the unspecified group instead. The raw result was retained rather than silently edited into a better experiment. Structural validation did not catch that attribution nuance.

Regression checks also reproduced and fixed stale-review failures: changing an extracted date or significance now invalidates the evidence version, and changing episode selection or its challenge invalidates the depth review. Existing legacy evidence hashes remain unchanged. These checks protect the saved workflow; they do not grade narrative quality.

## Portable writing

New sessions use the career-sheet/v2 export contract. Each detail claim belongs in one field; a short lead may reuse it intentionally. Account limits select supported claims and carry the same original excerpts as other facts. Raw coverage notes, rejected interpretations and audit instructions remain in the research journal. Person-facing questions are chosen once in the account plan.

Collective actors and action states still require a semantic review of the prose. Reference checks do not establish that the model has described ownership correctly. Journals without the export version rebuild through the legacy rules; changing the contract does not rewrite earlier trial outputs.
