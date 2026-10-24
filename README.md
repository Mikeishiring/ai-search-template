# AI search template

Trace work from its first proposal through delivery, corrections and later use. Keep exact sources and distinguish your contribution from everyone else's.

**This is an offline prototype, not a connected personal-search app.** You can inspect synthetic AI experiments or import selected records into your own local dashboard. There is no Slack, Notion, GitHub or ATS login button. Live adapters and automatic personal research are not implemented.

| Your goal | Working path |
|---|---|
| See the research approach | Open the included [synthetic report](AI-SEARCH-MVP.html) locally; no account needed |
| Build your own dashboard | Follow the local walkthrough below; Python 3.11+ only |
| Connect an AI host | Follow [MCP setup](docs/MCP.md); the bundled bridge serves fictional cases only |
| Connect real accounts | Read [Sources](docs/SOURCES.md); collect permitted exports or build the missing adapter |

## Get a local copy

Use GitHub's **Use this template** for reusable code, then download its ZIP and extract it, or check it out with Git. Open a terminal in the repository folder containing `personal.py`. No Python packages need installing.

Run `python --version`; it must show 3.11 or later. On Windows, `py -3` may be available; on macOS/Linux, use `python3`. Substitute that command for `python` below. The code is platform-neutral, but this walkthrough was exercised on Windows only.

Keep personal evidence outside this checkout, even if your copy of the template is private. Use a separate folder and, for remote backup, a separate empty private repository.

## Build your first dashboard

Run these commands **from the repository root**. The supplied records are fictional. `../my-evidence` creates a sibling folder; choose another name if it already exists.

```sh
python personal.py init ../my-evidence --title "My work evidence" --synthetic
python personal.py import-json ../my-evidence examples/first-records.json
python personal.py add-claim ../my-evidence --source chat --id proposal-01 --actor "Contributor 01" --state offered --statement "Contributor 01 offered to draft a troubleshooting guide." --quote "I can draft a troubleshooting guide for the support team." --limits "This proposal does not establish delivery or adoption."
python personal.py build ../my-evidence
```

Open `../my-evidence/DASHBOARD.html` locally. Expect **2 imported records and 1 proposed claim**. Expand a source to inspect its text. The page does not contact a model or source account. This is separate from the historical synthetic experiment report.

For your own material, create a new empty workspace without `--synthetic`, rather than mixing it with the tutorial. Import selected UTF-8 `.md`/`.txt` files with metadata, or convert authorized exports into normalized JSON. [Source preparation and import commands →](docs/SOURCES.md)

Run `build` again after adding evidence or claims. New captures preserve older text, and claims anchored to an older revision get a re-review warning. Importing records does not generate claims. Use `add-claim`, or try the [optional personal-review prompt](prompts/PERSONAL-REVIEW.md) in an AI host you have chosen to trust with selected evidence. Automatic personal AI integration is not implemented.

## Where your data goes

The personal CLI reads the supplied file and writes local JSON and HTML. It does not connect to services, call a model, run Git or upload anything. The HTML embeds source text: keep it private too. Clicking an original-source link contacts that service.

An AI host may send records to its model provider. GitHub backup sends committed files to GitHub. Neither happens through `personal.py`. A private repository is access-controlled remote storage, not encryption that only you can decrypt. [.gitignore does not make a public repository safe for private data. Read the privacy guide →](docs/PRIVACY.md)

## What is missing

The local path supports manual text/JSON import, one source anchor per proposed claim, immutable captures and a report. It does **not** parse raw Slack ZIPs, PDFs or ATS CSVs; enumerate real threads; resolve identities; infer achievements; combine multi-source claims; compute reliable personal interview counts; or review a claim's meaning. A checked quotation can still support a misleading sentence.

The synthetic demo works from a fresh checkout, but its latest experiment still loses reviewer credit and overstates a planned action. It is not a production benchmark. [First-use audit and remaining gaps →](docs/FIRST-USE-AUDIT.md)

## Inspect the research prototype

```sh
cd ai-search-mvp
python -m unittest discover -s tests -q
python cli.py report
```

The report is written one directory above, at `AI-SEARCH-MVP.html`. These commands inspect saved synthetic experiments; they do not build your personal dashboard or run new AI research. Node.js is optional for `node tests/check_report.cjs`, which checks behavior in a simulated DOM, not a rendered browser.

From the repository root, run `python -m unittest discover -s tests -q` for the separate personal-workspace tests. [MCP setup](docs/MCP.md) includes a no-model connection test.

## Research method and reuse

- [Specification](SPEC.md): proposed research loop and connector contracts; many features remain unimplemented.
- [Historical experiments](ai-search-mvp/README.md): evidence, failures and evaluation limits.
- [Prompts and schemas](ai-search-mvp/model): instructions used in those experiments.
- [Synthetic fixtures](ai-search-mvp/fixtures): fictional cases; `.gold.json` answer keys are evaluator-only inputs.

No private career records, credentials or host session databases are included. Historical model launch scripts assume Windows/npm Codex and are not the newcomer setup path. Code, documentation and synthetic examples are [MIT licensed](LICENSE).
