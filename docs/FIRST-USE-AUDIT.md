# First-use audit

24 October 2026. Tested with fictional records only. No personal archive or live account data was used.

## What a new user encountered

The original fresh checkout passed 78 tests and rebuilt its historical report. It could demonstrate the research experiments, but could not fulfill the implied personal workflow. “Use your own history” ended with “build adapters.” There was no personal import command, no dashboard entry point for their data and no concrete MCP handshake check.

The demo MCP and latest experimental server use different tool contracts. Submitted demo reviews are saved but not displayed in the historical dashboard. The first README also failed to distinguish viewing saved AI output from running a new model. These are product gaps, not wording problems alone.

## Changed in this pass

| Finding | Change | Limit |
|---|---|---|
| No personal source-to-dashboard path | Added separate workspace initialization, text/normalized-JSON import, source-anchored claims and local HTML generation | Manual preparation and claims; no autonomous research |
| Data could be placed beside public code | Workspace creation rejects paths inside this checkout; docs require separate storage/history | Cannot detect cloud sync or unrelated public repositories |
| “Connect sources” was vague | Added per-source preparation routes and clear absent-adapter list | No live authentication or export parser added |
| Model and privacy boundaries unclear | Documented local CLI, browser links, AI-provider handoff and GitHub backup separately | No encryption or universal secret scanning |
| No reproducible MCP setup check | Added no-model stdio handshake and inventory probe | Tests local server, not any particular AI host |
| Source changes could invalidate claims | Immutable captures, exact quotation checks and stale-claim warnings | Manual re-review; no automatic synthesis or approval |

## Still blocking a connected product

1. **Real collection is missing.** No live adapters, OAuth flow, authorized scope picker, rate-limit handling, thread enumeration, attachment extraction or incremental synchronization. Export conversion is manual.
2. **Personal research is missing.** No agent loop consumes the private workspace. The historical prototype and personal workspace are separate paths. Adding an AI account does not join them.
3. **A faithful story is not guaranteed.** One record per proposed claim cannot express multi-source evidence properly. Exact quotes do not stop overstated delivery or missing reviewer credit. Claims have no approve/reject workflow.
4. **Coverage is unknown.** Imported record count is not a percentage of an archive. The personal dashboard has no live coverage ledger or automatic follow-up queue.
5. **Source semantics are limited.** Dates have day precision; parent IDs are shown rather than resolved. Identity merging, copied records, metric denominators and cross-platform duplicates remain unsolved.
6. **The storage layer is small.** JSON is capped at 20 MiB, single-writer, with no concurrent editing protocol, migrations, encrypted storage or full-disk backup. Atomic file replacement prevents partial writes, not multi-process lost updates.
7. **Portability and UI evidence are bounded.** The source is standard-library Python; the walkthrough was run on Windows, not on macOS/Linux. HTML escaping and structure are checked, but browser layout, keyboard/touch behavior and visual fit have not been rendered in this session because of the existing local-file browser restriction.

## Verification

Fresh-checkout historical tests: 78 passed. Personal workspace tests: 10 passed. Those cover separate-directory enforcement, refusal to overwrite, atomic invalid-batch rejection, exact and ambiguous quotations, duplicate imports, preserved revisions, stale claims, source-tampering detection, safe HTML escaping and operation without network/subprocess access.

The CLI walkthrough uses two fictional records and one offered-state claim. The no-model MCP probe verifies initialization, six tools and synthetic inventory. Historical report tests preserve saved evidence and check interactions in a simulated DOM; they do not establish a rendered-browser pass.

The next useful increment is one real read-only adapter with a bounded end-to-end test: declare scope, enumerate complete threads, preserve original records, track missing material, produce reviewable multi-source claims and refresh the private dashboard. Adding more connectors before that path works would multiply the gaps.
