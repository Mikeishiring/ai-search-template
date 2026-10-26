# Research fictional sources and build the sheet

The integrated demo starts with a question and source boundaries. An agent chooses its own reads, follows the saved research queue, keeps evidence notes, checks a draft and selects where its claims belong in the sheet. The compiler carries those checked sentences and exact source excerpts into the existing HTML.

## Run the complete flow

Requirements: Python 3.11 or later and an installed, authenticated Codex CLI. The supplied launcher currently locates the Windows npm installation. The renderer and source tools use the Python standard library.

From the project root, choose an existing output folder outside the checkout:

```sh
python career_context.py research-demo ../research-story.html
```

This command makes a remote model call through your Codex account. It accepts **only the fixed fictional case**, not a personal input path. The researcher starts with the scope and reads through the isolated `synthetic_research` tools. User configuration, prior conversations, memory, shell, browser, unrelated apps and skill discovery are disabled for that invocation. The source server has an additional file-read allowlist and cannot make network calls. These controls limit this experiment; they are not a general-purpose security sandbox.

The output is one portable HTML draft. Its working state lives beside it in `.research-story-research/`, including source-call receipts, notes, checked drafts, the selected layout and build receipt. You can choose a different private location with `--workspace`. The launcher reuses the existing ignored CLI state directory instead of creating another state-database copy for every session.

## Resume or rebuild

```sh
# Continue the same saved journal after a stopped model attempt
python career_context.py research-demo ../research-story.html --resume

# Rebuild an already sealed run without a model call
python career_context.py research-build ../.research-story-research ../research-story.html --force
```

An existing output is preserved unless `--force` is given. Resume retains the source and request budgets, evidence and queue; it does not reset the experiment or conceal the first attempt. A sealed journal is rebuilt locally. An unfinished launch must be inspected before another launch. A stale or invalid draft cannot produce a sheet.

## How research reaches the HTML

- **Source reads:** existing tools expose search, bounded earlier/main/later windows, original records, nested context and attachment status. Sources remain read-only.
- **Evidence notes:** `save_notes` stores findings and actor/action/state assertions. `writing_packet` recovers already-read originals and exact spans without new source charges.
- **Draft check:** claims cite exact spans and saved attributions. Material read records need representation or a reason for omission. This checks structure, not whether the source supports the interpretation.
- **Sheet plan:** the agent maps claim IDs into overview, summary, context, aim, contribution, decisions, shared work and outcome. Every claim must survive in an account field. No separate prose rewrite occurs during compilation.
- **Finish check:** known source work, writing obligations and a current sheet plan govern the stopping receipt. Remaining work stays explicit at a real budget limit.
- **Build:** the compiler verifies the journal and current draft, includes only selected excerpts, keeps unknowns and rejected interpretations, and invokes the existing renderer. The sheet stays a draft for the person to review.

The model has 45 charged source calls and 80 total requests for this case. Local notes and cached recovery cost no source calls but count as requests. These are test limits, not recommended budgets for a person's career.

## Privacy and scope

The corpus and scope are fixed and hash-checked. Relabelling a session as synthetic or changing its subject cannot put personal material into this launcher. Excluded sources and post-horizon records are not readable. Instructions in a source do not change scope. The evaluator's rubric is not available through the MCP.

The public fixture and any published result are fictional. Never copy your private journal or source archive into this repository. To create a sheet from real selected material, use [local setup](LOCAL-CONTEXT.md) and the [agent skill](../skills/career-context-sheet/SKILL.md). The policy controls which local captures a chosen AI host may receive. The demo launcher does not connect real accounts or automatically send personal exports to a model.

## What the test can establish

The [case](../ai-search-mvp/fixtures/sheet.corpus.json) includes two chat locations, documents, selected email/calendar records and code reviews. Its public [rubric](../ai-search-mvp/fixtures/sheet.gold.json) checks decisions, shared credit, nested corrections, later use, action state and personal meaning. The implementation assistant authored both; the model researcher sees neither the rubric nor the prior conversation.

Passing the build proves that checked claim sentences and selected excerpts reached the sheet. It cannot prove that the model retained every important meaning or interpreted every source fairly. Assess the first account against the rubric, including limitations and misses; do not turn exact citations or a completed queue into a semantic-success claim.

The [first-run result](RESEARCH-STORY-RESULT.md) preserves the generated story, source receipts, one semantic omission and the disclosed UTF-8 repair.
