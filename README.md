# Career Context AI

**Keep the context behind your work.**

Turn selected notes, documents and conversations into one readable file: what you did, why it mattered, who else contributed and what happened next. Give that file to an agent for a resume, interview or career question without rebuilding your story each time.

![A fictional career-context sheet with readable work accounts and controls for copying context to an agent](docs/career-context-preview.png)

Use work documents only with an approved model and sources you are allowed to share.

## Try the sheet

[Download the project](https://github.com/Mikeishiring/career-context-ai/archive/refs/heads/main.zip), extract it and open **[CAREER-CONTEXT.html](CAREER-CONTEXT.html)** in a browser. The example is fictional and works offline.

Open a work account, follow its sources, then try **View agent text**. **Copy for an agent** carries the same account, including shared credit and limits. GitHub displays HTML as source; use the downloaded file.

For a notebook with a custom navigation menu, quarterly work, visual evidence and interview follow-ups, open **[CAREER-NOTEBOOK.html](CAREER-NOTEBOOK.html)**. This edition uses the same fictional source packet, with an explicit quarterly companion. [Notebook guide](skills/career-context-sheet/references/notebook.md).

## Make it yours

Give your agent the complete [career-context-sheet](skills/career-context-sheet/SKILL.md) folder and selected material. It includes the research guidance, format, renderer and visual template.

> Help me build a career-context sheet using this skill. Reuse what I have already told you; establish the work, sources and privacy boundaries that are still unclear. Investigate my decisions, shared contributions and later outcomes. Preserve my voice and uncertainty, ask what the records miss, and create one private HTML file I can keep.

Start with one useful account. The agent should pursue consequential questions and challenge its first draft; you should not need to keep asking it to go deeper.

[Get started with Claude, Codex or another agent](docs/GETTING-STARTED.md).

Ask the agent to [prepare an interview](skills/career-context-sheet/references/interview-prep.md). It selects the evidence and drafts an introduction, answers, story chapters and timelines from your context. You review, practise and resolve genuine gaps.

## What you keep

- **Your work in context:** personal decisions, shared work, outcomes and unfinished questions.
- **Inspectable evidence:** selected excerpts remain distinct from summaries and interpretation.
- **One portable HTML file:** readable accounts, plain agent text, structured context and selected images travel together.

The renderer uses Python 3.11+ with no packages or network calls. The agent you choose does the research and writing. Live source connectors are supplied by your host; installing this project does not connect accounts.

## For developers

The [product contract](docs/PRODUCT.md) defines the release criteria. The core product is the skill and portable sheet. Build the standalone skill bundle without the research harness:

```sh
python tools/build_skill.py ../career-context-sheet.zip
```

The optional local research server adds scoped export access and resumable evidence review. Experiments remain available in the repository so their results and failures can be inspected.

| Need | Guide |
|---|---|
| Create, update or share a sheet | [Getting started](docs/GETTING-STARTED.md) |
| Select local exports and use the research server | [Local context](docs/LOCAL-CONTEXT.md) |
| Understand storage and sharing | [Privacy](docs/PRIVACY.md) |
| Inspect research methods and results | [Research guide](ai-search-mvp/README.md) · [Event retention](docs/EVENT-RETENTION.md) · [Batch extraction](docs/BATCH-EXTRACTION.md) · [Deep-review result](docs/DEEP-RESEARCH-RESULT.md) |
| Build, test or contribute | [Contributing](CONTRIBUTING.md) |

The research server currently uses selected snapshots. Live connectors, automatic refresh and reliable semantic review remain under development.

[MIT licensed](LICENSE).
