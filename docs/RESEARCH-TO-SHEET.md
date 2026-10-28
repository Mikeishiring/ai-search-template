# Research fictional sources and build the sheet

The integrated demo starts with a question and source boundaries. An agent chooses its own reads, follows the saved research queue, keeps evidence notes, checks a draft, challenges its first sheet plan and reviews the depth of every account. The compiler carries those checked sentences and exact source excerpts into the existing HTML.

## Run the complete flow

Requirements: Python 3.11 or later and an installed, authenticated Codex CLI. The launcher uses the Codex executable on PATH, with a Windows npm fallback. The renderer and source tools use the Python standard library.

From the project root, choose an existing output folder outside the checkout:

```sh
python career_context.py research-demo ../research-story.html
```

This command makes a remote model call through your Codex account. It accepts **only the fixed fictional case**, not a personal input path. The researcher starts with the scope and reads through the isolated `synthetic_research` tools. User configuration, prior conversations, memory, shell, browser, unrelated apps and skill discovery are disabled for that invocation. The source server has an additional file-read allowlist and cannot make network calls. These controls limit this experiment; they are not a general-purpose security sandbox.

The output is one portable HTML draft. Its working state lives beside it in `.research-story-research/`, including source-call receipts, notes, checked drafts, the selected layout and build receipt. You can choose a different private location with `--workspace`. The launcher reuses the existing Codex runtime state directory outside the public project instead of creating another state-database copy for every session.

## Resume or rebuild

```sh
# Continue the same saved journal after a stopped model attempt
python career_context.py research-demo ../research-story.html --resume

# Rebuild an already sealed run without a model call
python career_context.py research-build ../.research-story-research ../research-story.html --force
```

An existing output is preserved unless `--force` is given. Resume retains the source and request budgets, evidence and queue; it does not reset the experiment or conceal the first attempt. A sealed journal is rebuilt locally. New sessions require `career-depth/v1`; historical sealed journals remain rebuildable with an explicitly legacy receipt and do not gain a depth-review claim. The supervisor resumes interrupted workers automatically within the saved attempt and time limits. Runtime output is streamed to disk; the journal, not the final response, is the research checkpoint. A stale or invalid draft cannot produce a sheet.

## Automatic recovery and turning points

```sh
python career_context.py research-demo ../observatory-story.html --case turning-points --max-attempts 3 --timeout 600
```

The observatory fixture tests a responsibility change in an ordinary calendar message, a stopped experiment, another person's later use, shared implementation and a partial handoff. Its excluded source contains a fictional canary. It contains no personal pilot material.

New sessions require an event-level turning-point review after story selection. `turning_point_packet` returns both selected and reserve/excluded events. The agent must classify each event, connect consequential changes to a selected account, and retain them in supported prose or give a specific omission reason. `save_turning_points` binds decisions to the current evidence, claims, layout and episode selection. Structural completion cannot certify the model's judgment.

The supervisor preserves each attempt under `research-run/`. Default limits are three worker attempts of up to one hour each; `--max-attempts` and `--timeout` set the limits before starting. These limits persist across resumes, alongside the source-call and request budgets. A timeout, worker error or unfinished draft can trigger another worker without a human depth prompt. `resume_packet` recovers the saved draft, plan, last depth audit and refusals. A valid finish can be built even if the response message was lost.

An OS lock prevents competing runners or research servers. After a worker stops, only a torn final journal append can be recovered automatically; the original tail is preserved. Corruption in a completed line, changed sources/policy/code, unexpected tools, an unresolved live worker or exhausted limits stops recovery. The runner never grants new source permissions, makes a stale review valid, or labels an unfinished journal complete.

If the supervisor or computer itself stops, run the same command with `--resume` to recover the durable state. This is not a background service that restarts after a computer shutdown. An uncertain surviving worker blocks restart rather than racing another writer. Automatic recovery does not make model processing offline; the configured provider still receives admitted evidence.

## How research reaches the HTML

- **Source reads:** existing tools expose search, bounded earlier/main/later windows, original records, nested context and attachment status. Sources remain read-only.
- **Evidence notes:** new sessions retain every source section through `save_extraction`; legacy sessions use `save_notes`. `writing_packet` recovers already-read originals and exact spans without new source charges.
- **Draft check:** claims cite exact spans and saved attributions. Material read records need representation or a reason for omission. This checks structure, not whether the source supports the interpretation.
- **Sheet plan:** the agent maps claim IDs into overview, summary, context, aim, contribution, decisions, shared work and outcome. Every claim must survive in an account field. No separate prose rewrite occurs during compilation.
- **Turning points:** all retained events receive explicit review, including links from reserve episodes into selected stories.
- **Depth review:** question-led probes must precede each account's first plan, span all selected source groups, and include a fresh challenge after that plan. Ten lenses, every material actor/action and the proposed through-line are reviewed against current evidence and prose.
- **Finish check:** known source work, writing obligations, a current plan and a current depth review govern the stopping receipt. Accessible pending depth questions block completion while budget remains. Remaining work stays explicit at a real budget limit.
- **Build:** the compiler verifies the journal and current draft, includes only selected excerpts, keeps unknowns and rejected interpretations, and invokes the existing renderer. The sheet stays a draft for the person to review.

The integrated flow allows 450 charged source calls and 1,600 total requests. The source-call ceiling is ten times the first demonstration's capacity; the total also accommodates extraction and batched attribution review. Local notes, reviews and cached recovery cost no source calls but count as requests. The demo launcher allows up to one hour per attempt. These are ceilings, not a promise of ten times the elapsed time or a target for repetitive calls. The [full research flow](DEEP-RESEARCH-FLOW.md) explains the enforced passes, local state and limits. Historical experiment classes retain their original budgets.

## Privacy and scope

The corpus and scope are fixed and hash-checked. Relabelling a session as synthetic or changing its subject cannot put personal material into this launcher. Excluded sources and post-horizon records are not readable. Instructions in a source do not change scope. The evaluator's rubric is not available through the MCP.

The public fixture and any published result are fictional. Never copy your private journal or source archive into this repository. To create a sheet from real selected material, use [local setup](LOCAL-CONTEXT.md) and the [agent skill](../skills/career-context-sheet/SKILL.md). The policy controls which local captures a chosen AI host may receive. The demo launcher does not connect real accounts or automatically send personal exports to a model.

## What the test can establish

The [case](../ai-search-mvp/fixtures/sheet.corpus.json) includes two chat locations, documents, selected email/calendar records and code reviews. Its public [rubric](../ai-search-mvp/fixtures/sheet.gold.json) checks decisions, shared credit, nested corrections, later use, action state and personal meaning. The implementation assistant authored both; the model researcher sees neither the rubric nor the prior conversation.

Passing the build proves that checked claim sentences and selected excerpts reached the sheet. It cannot prove that the model retained every important meaning or interpreted every source fairly. Assess the first account against the rubric, including limitations and misses; do not turn exact citations or a completed queue into a semantic-success claim.

The [first-run result](RESEARCH-STORY-RESULT.md) preserves the generated story, source receipts, one semantic omission and the disclosed UTF-8 repair.

The [deep-review result](DEEP-RESEARCH-RESULT.md) records the next uncoached trial, its restored proposer credit, remaining alias omission and receipt usability repair.

The [turning-point and recovery result](TURNING-POINTS-AND-RECOVERY.md) records the fictional story check, a deliberately interrupted live worker, automatic continuation and remaining limits.
