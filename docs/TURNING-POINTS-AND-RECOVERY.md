# Turning points and interruption recovery

New research sessions review every retained event for changes in responsibility, handoffs, stopped work, later use, changed approaches, operating decisions and delivery. The review includes reserve and excluded material. Changed evidence, claims or selection invalidates the decisions. The standalone skill carries the same research guidance; enforcement is provided by the optional local server.

Version 2 requires the actual prose: mark essential events, quote every represented claim and explain its actor/action/state fidelity. Essential events cannot be omitted. Linked qualifications must survive in the same account. The depth review also quotes the opening's interpretation and limit, so the connection between episodes reaches the reader. These checks make review explicit; they cannot decide whether the researching agent's judgment is true. Existing version 1 journals keep their original checks.

`research-run` supervises an approved local workspace. `research-demo` uses the same supervisor with fixed fictional inputs. Workers recover the saved draft, checked plan, review and remaining work through `resume_packet`. Automatic retries retain the original source boundaries, request budget and attempt/time limits. A valid journal can be built after a lost response; a partial journal cannot be presented as complete. After a stable allowed finish receipt, the supervisor gives the worker five seconds to return, then stops it and revalidates the journal, policy and build gates. The receipt records this separately from a timeout or normal exit.

The [fictional observatory case](../ai-search-mvp/fixtures/turning-points.corpus.json) places a responsibility change in an ordinary calendar message, separates a proposed handoff from its partial completion, includes a stopped experiment and follows another person's use of a checklist. It also includes a small briefing choice, a required approval sequence and a delivered observing night. A private-source canary is outside the [selected scope](../ai-search-mvp/fixtures/turning-points.scope.json).

## Current integrated check

The expanded eleven-record case completed in one authenticated model attempt: 36 retained events, 25 claims, two accounts and 36 selected excerpts. It used 67 requests and 37 charged source calls in 215.22 seconds. No human depth prompt or manual prose edit was supplied. The worker was stopped after its durable finish receipt; the supervisor accepted the checked journal and built the sheet without another attempt. Its exit code was 1 from termination, with `stopped_after_finish` true and `timed_out` false.

The story preserves the announced rota split and the later cancelled-volunteer exception; written instructions versus a ten-minute walk-through; equipment approval before opening the queue; delivered event leadership and shared work; the stopped controller trial; and qualified later checklist use. The opening connects the two accounts and retains a limit. The excluded-source canary is absent.

The integrated toolkit suite passed 206 tests; the underlying research suite passed 87. Offline MCP, multi-source checks, reproducible public examples and standalone bundle checks passed. Both the shipped example and freshly generated story passed browser checks at 320, 375, 768 and 1440 pixels, including keyboard navigation, clipboard fallback, downloads, no-JavaScript reading and print. Rendered desktop and mobile output were inspected. These checks establish the tested fictional behavior, not semantic completeness for a person's archive.

## Earlier interruption trial

The following results used the earlier eight-record version of the fictional case and version 1 review:

| Check | Observed result |
|---|---|
| Toolkit regression suite | 167 tests passed |
| Underlying research suite | 87 tests passed |
| Offline MCP and multisource checks | Passed |
| Fictional demo and standalone skill build | Passed |
| Fresh authenticated model trial | 8 admitted records, 26 retained events, 15 claims, 26 exact excerpts; 57 requests and 29 charged source calls |
| Fresh story semantics | Responsibility change, partial handoff, stopped experiment, shared credit, qualified later use and attributed reflection retained |
| Forced live interruption | First worker terminated after the checked plan at journal sequence 37; second worker launched automatically |
| Recovery | `resume_packet` returned the exact saved draft and plan at sequence 39; zero original-record rereads and one new source call for further research |
| Recovered story | 17 claims, 26 exact excerpts; current turning-point, depth and finish gates; 55 total requests and 28 charged source calls |
| Excluded source | Canary absent from both completed sheets and full-read records |

The uninterrupted worker finished with exit code 0 after 237.11 seconds. In the forced test, worker 1 ended with exit code 1 after 60.62 seconds; worker 2 finished with exit code 0 after 69.66 seconds. The supervisor made one automatic retry. No human follow-up prompt, manual journal repair or prose edit was supplied. These are separate generated stories, not a controlled timing comparison.

The failure paths are tested in [the recovery suite](../tests/test_research_runner.py): real local worker timeout, abrupt lock-owner exit, torn final append, lost final response, persistent retry limits, changed code, revoked policy, unexpected tools and a worker whose termination is uncertain. [Turning-point tests](../tests/test_turning_points.py) require review of a reserve handoff, reject unrelated claim references, preserve announced state and invalidate stale decisions. A finished fixture is compiled through the real sheet builder.

Testing exposed three issues that were corrected. A failure receipt could previously bypass the live-worker check; recovery now requires verified termination or a safe liveness check. Resume fingerprints omitted some validation schemas and the HTML template; those dependencies are now included. A preliminary live attempt interpreted “do not restart discovery” as prohibiting initial discovery on an empty journal; the instruction now explicitly permits starting already-authorized research. That unsuccessful attempt and the fault-injection harness's premature assertion were preserved separately from the successful forced test.

The attempt budget is finite and persists across invocations. An unresolved live worker, revoked or changed source policy, corrupted completed journal line, changed implementation or unexpected tool stops recovery. A torn final append is preserved before truncation. If the supervisor or computer stops, the same command must be started again; this is not an operating-system background service.

These results cover a small constructed case and deliberate failure tests. They do not establish whole-archive semantic completeness or guarantee that every model identifies every important transition. The review enforces explicit decisions and evidence references, not their truth. Both stories remain drafts; some summary and detail prose repeats. Visual QA was not performed for this backend change. No private pilot captures, model logs or personal outputs are included in this public report.
