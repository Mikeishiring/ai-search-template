# AI search template

Reconstruct how work happened across messages, documents and code. Keep the sources, distinguish personal work from shared ownership, and follow a launch through to later use.

This repository contains the method, prompts, a local Python prototype and fictional test stories. It contains no personal career archive. The prototype replays synthetic sources; live Slack, Notion, GitHub and ATS connectors are not implemented.

## Try it

Requires Python 3.11 or later. The offline demo uses only the standard library; no account, API key or model call is needed.

```sh
cd ai-search-mvp
python -m unittest discover -s tests -v
python cli.py report
```

Open `AI-SEARCH-MVP.html` at the repository root. It is a self-contained local report. To run the deterministic examples rather than inspect saved results:

```sh
python cli.py run training
python cli.py evaluate training
python cli.py run challenge
python cli.py evaluate challenge
python cli.py run search_only
python cli.py report
```

An AI host can launch `python mcp_server.py` from `ai-search-mvp/` and use [the research prompt](ai-search-mvp/RESEARCH-PROMPT.md). That bridge exposes synthetic data only. The model host controls inference and its data handling. The saved autonomous experiments used isolated Codex invocations; their historical launch scripts assume a Windows/npm installation and are not a portable model integration.

## Start with these

- [Research process and connector specification](SPEC.md): scope, coverage, thread traversal, cross-platform links and prompts.
- [Prototype and experiment notes](ai-search-mvp/README.md): implementation, failures and reproduction commands.
- [Research prompt](ai-search-mvp/RESEARCH-PROMPT.md) and [model prompts and schemas](ai-search-mvp/model): reusable instructions and output contracts.
- [Synthetic fixtures](ai-search-mvp/fixtures) and [saved results](ai-search-mvp/runs): inspectable cases, including failures. Answer keys are evaluator-only inputs.

## Use it with your own history

Create a separate **private repository** for your own sources, notes, claims, reviews and resume. Start from an empty private repository; a public template fork is still a public publication surface.

Keep these as separate working directories and Git histories. Do not use a shared data folder, submodule, shared Git remote or an automatic private-to-public sync. Keep credentials in your local credential store or environment, outside both repositories. A private GitHub repository is remote storage with access control; it is not local-only or end-to-end encrypted storage.

Define the question, permitted sources, dates and exclusions before connecting real systems. Build adapters that allow only the required reads. Preserve exact source text and timestamps, then distinguish proposals, requests, completed work, measurements and interpretation. A model service may receive supplied evidence: choose its access and retention arrangements deliberately before sending private material.

Publish selected lessons or examples through a new reviewed export. Renaming people is not sufficient anonymization: quotations, timelines, compensation, project names and internal links may still identify them. Never copy a private archive here and try to clean it afterwards.

## What the tests establish

The latest saved synthetic run read 39 of 39 accessible records and retained 70 exact quotation spans. Manual review found 11 of 12 themes complete and one partial. It still lost reviewer attribution and overstated a planned action in prose. A failed connection launch preceded the substantive attempt and is disclosed in the assessment.

Passing citation and bookkeeping checks does not prove a faithful story. The report keeps semantic criticism alongside the original output. These are small synthetic experiments, not a production accuracy benchmark.

This release includes selected synthetic result artifacts, not host session databases, transport logs or private working files. The publication manifest records the included files. No default deployment or automatic publication is configured.
