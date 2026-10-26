# Career Context AI

**Give your AI the context behind your work.**

Keep your contributions, decisions, shared work and outcomes in one readable file. Attach it to an agent when you want help with a resume, interview or career question, without starting your story again.

![A fictional career-context sheet with readable work accounts and controls for copying context to an agent](docs/career-context-preview.png)

## Try it

1. [Download the project](https://github.com/Mikeishiring/career-context-ai/archive/refs/heads/main.zip) and extract it.
2. Open **[CAREER-CONTEXT.html](CAREER-CONTEXT.html)** in your browser. The example is fictional and works offline.
3. Try **View agent text**, expand a work account, or follow one of its sources. **Copy for an agent** carries the same context, including limits and shared credit.

No installation or account is needed to read a sheet. GitHub displays HTML as source; open the downloaded file to use it.

## Make it yours

Start with a project you remember well. Give your agent the bundled [career-context skill](skills/career-context-sheet/SKILL.md), selected notes and this request:

> Help me make a career-context sheet. First establish what work to cover, which sources we can use and what should stay private or out of scope. Reuse anything I have already told you. Follow unresolved questions within that scope without waiting for repeated prompts. Build the story from my decisions, shared work and later outcomes, preserving uncertainty. Ask what the records miss or misrepresent. Create one private HTML file I can read and give to another agent.

The [getting-started guide](docs/GETTING-STARTED.md) covers using the skill, preparing a sheet manually and updating an existing file. You can begin with one account.

If you prefer a terminal, use **Python 3.11 or later**, with no packages to install:

```sh
# Rebuild the fictional example outside the project
python career_context.py demo ../career-context-demo.html

# Render your own selected context, stored outside this checkout
python career_context.py render ../my-context/context.json ../my-context/career-context.html
```

Run commands from the extracted project folder. On macOS/Linux, use `python3` if needed; on Windows, `py -3` may be available. An existing output is preserved unless you add `--force`.

## What travels with your sheet

- **Readable work accounts:** context, contribution, decisions, shared credit and outcomes.
- **Sources and open questions:** selected excerpts stay distinct from summaries; unknowns remain explicit.
- **The same context for an agent:** plain text and structured JSON are included in the HTML. Selected images stay embedded in the file.

Setup, import, status, `demo` and `render` make no model calls or uploads. The optional `research-demo` invokes authenticated Codex using fixed fictional sources. A local research server can expose selected private captures to an AI host only when the workspace policy explicitly allows it. Live Slack, Notion, GitHub and ATS connectors are **not included**.

## Keep personal context private

Your HTML includes the selected source text. Keep real inputs and outputs **outside this public repository**, and inspect the whole file before sharing it. Copying text to an AI host sends it through that host's data handling; local generation does not.

The public project contains reusable tools and fictional examples. It does not contain a personal career archive. [Privacy and storage guide](docs/PRIVACY.md).

## Go deeper

| You want to... | Start here |
|---|---|
| Create or update a portable sheet | [Getting started](docs/GETTING-STARTED.md) |
| Choose sources, DM access and local storage | [Your local context](docs/LOCAL-CONTEXT.md) |
| Keep source versions and proposed claims | [Local evidence workspace](docs/EVIDENCE-WORKSPACE.md) |
| Prepare selected exports | [Source preparation](docs/SOURCES.md) |
| Try the fictional MCP research server | [MCP setup](docs/MCP.md) |
| Test research across channels and sources | [Multi-source tests](docs/MULTISOURCE.md) |
| Turn research into a recognizable personal story | [From evidence to story](docs/FROM-EVIDENCE-TO-STORY.md) |
| Understand the enforced deep research loop | [Full flow](docs/DEEP-RESEARCH-FLOW.md) |
| Preserve events and compare unused stories before finishing | [Event retention](docs/EVENT-RETENTION.md) |
| Run research through to an HTML sheet | [Integrated fictional demo](docs/RESEARCH-TO-SHEET.md) |
| Inspect the deeper run and its remaining gap | [Deep-review result](docs/DEEP-RESEARCH-RESULT.md) |
| Inspect the first unprompted story and its limits | [Research-to-sheet result](docs/RESEARCH-STORY-RESULT.md) |
| Inspect the experiments and their failures | [Research guide](ai-search-mvp/README.md) / [saved report](AI-SEARCH-MVP.html) |
| Understand the proposed research engine | [Specification](SPEC.md) |
| Improve the project | [Contributing](CONTRIBUTING.md) |

This is a local toolkit with selected-export research. Live connectors, automatic refresh and reliable semantic review still need development. The experiments retain missed context and attribution errors so those limits can be inspected.

[MIT licensed](LICENSE). Previously named **AI search template**; existing research commands and file formats remain compatible.
