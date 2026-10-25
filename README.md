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

> Help me make a career-context sheet. Start with what I tell you about my work. Keep my contribution, other people's work, outcomes and uncertainties distinct. Ask only for missing facts that would change the account. Create one private HTML file I can read and give to another agent.

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

The local tools make no model calls or uploads. AI assistance comes from the agent you choose. Live Slack, Notion, GitHub and ATS connectors are **not included**; the bundled MCP server serves fictional research cases only.

## Keep personal context private

Your HTML includes the selected source text. Keep real inputs and outputs **outside this public repository**, and inspect the whole file before sharing it. Copying text to an AI host sends it through that host's data handling; local generation does not.

The public project contains reusable tools and fictional examples. It does not contain a personal career archive. [Privacy and storage guide](docs/PRIVACY.md).

## Go deeper

| You want to... | Start here |
|---|---|
| Create or update a portable sheet | [Getting started](docs/GETTING-STARTED.md) |
| Keep source versions and proposed claims | [Local evidence workspace](docs/EVIDENCE-WORKSPACE.md) |
| Prepare selected exports | [Source preparation](docs/SOURCES.md) |
| Try the fictional MCP research server | [MCP setup](docs/MCP.md) |
| Inspect the experiments and their failures | [Research guide](ai-search-mvp/README.md) / [saved report](AI-SEARCH-MVP.html) |
| Understand the proposed research engine | [Specification](SPEC.md) |
| Improve the project | [Contributing](CONTRIBUTING.md) |

This is a local toolkit, not a connected career platform. Source collection, automatic personal research and claim review still need development. The experiments retain missed context and attribution errors so those limits can be inspected.

[MIT licensed](LICENSE). Previously named **AI search template**; existing research commands and file formats remain compatible.
