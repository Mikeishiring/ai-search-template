# Small batches before story selection

Large source collections can lose meaning before a narrative is drafted: a model may dismiss a collaborator's work or compress a long original into a generic note. The optional `research-extract` command separates section extraction from episode selection. It processes four sections per model call, then saves accepted output into the journal used by the research server.

Run the local plan first; choose a model-call limit when ready. The [local-context guide](LOCAL-CONTEXT.md) explains source consent, storage, interruption and resume. Model processing uses the authenticated Codex service; keeping the archive locally does not mean inference runs locally.

## Fictional integration trial

The trial used the fixed [story-depth corpus](../ai-search-mvp/fixtures/story-depth.corpus.json) and its [scope](../ai-search-mvp/fixtures/story-depth.scope.json), plus an empty page and a short social aside. The private-message record was excluded. No desired story list or earlier narrative was supplied.

| Stage | Observed result |
|---|---|
| Bounded extraction | Three model calls; all 12 sections from 11 admitted originals retained |
| Retained evidence | 36 event items; two sections correctly retained without work events |
| Research and synthesis | One further model call; 75 research-tool calls |
| Finished sheet | Two work accounts with 29 selected source excerpts |
| Human follow-up prompts | None during extraction or synthesis |

Counts come from the local model receipts, accepted extraction outputs and compiled sheet in this trial. Two startup failures occurred before these completed calls: one restricted CLI launch and one invalid test-harness configuration. Both were preserved and corrected explicitly; the batch launcher did not automatically retry them. Completed model time was about five minutes. This is one constructed case, not a performance estimate or a whole-archive success rate.

The resulting accounts connected the initial request to implementation, an access error, correction, a rename, handover and limited later use. The second account retained teaching, another contributor's examples, reuse without the subject present and a subsequent correction. The prose kept collective decisions collective and distinguished reported local use from organisation-wide adoption. Empty content and banter did not become achievements.

The structural gates checked section coverage, citation scope, journal consistency, episode allocation and depth-review references. Source-by-source review separately assessed attribution and the retained sequence. Neither process establishes independent verification of source claims or the person's own interpretation of their career.

## Remaining limits

Small batches can miss context in another section. The story-building prompt therefore asks the host to join uncertain actors, dates and aliases against complete originals, preserving citations from both sides. The extractor cannot prove that it noticed every meaningful action. An event count is not an achievement count.

The launcher stops at its explicit call limit, preserves failed attempts and reserves journal capacity for synthesis. A large archive can still exceed the research budget. Whole-archive narrative quality, automatic semantic review and live-source discovery remain unproven. The finished artifact remains a draft for the person to review.
