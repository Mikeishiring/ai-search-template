# Bring selected sources into your workspace

The template has no live connectors. Signing into Slack or installing an MCP in an AI host does not connect this Python program. Use the manual path below, or implement the adapter contracts in [SPEC.md](../SPEC.md).

Start with one project and a date window. Record which locations you may access. Include earlier proposals, complete reply chains and later follow-ups. An exported page or search result does not establish that every relevant thread was read.

## Source routes

| Source | Obtain permitted material | Accepted today | Missing |
|---|---|---|---|
| Slack | Authorized export or selected complete conversations | Messages normalized into JSON with author and parent references | ZIP parser, user-ID mapping, thread pagination, attachments and live search |
| Notion | Selected Markdown export, including subpages when permitted | Individual `.md` files with metadata | ZIP traversal, database CSV conversion, author resolution and attachments |
| GitHub | Selected issues, PR discussions, reviews and code changes | Normalized JSON or selected text | API adapter, pagination, review-thread resolution and synchronization |
| ATS | Authorized report/export with defined dates and population | Selected rows converted into textual records with report definitions | CSV importer, event deduplication, interviewer attribution and metrics |

Slack export availability depends on workspace plan, role and permissions; members cannot assume access to DM/private-channel exports. [Slack export documentation](https://slack.com/help/articles/201658943-Export-your-workspace-data).

Notion supports Markdown/CSV exports and inclusion of subpages, subject to access and workspace controls. Unzip outside the template. This importer reads selected Markdown, not the export structure. [Notion export documentation](https://www.notion.com/help/export-your-content).

A future GitHub adapter should allow required read endpoints and preserve pagination and review relationships. A commit proves a change, not adoption. [GitHub REST guide](https://docs.github.com/en/rest/using-the-rest-api/getting-started-with-the-rest-api).

A future Ashby adapter must allow operations by semantics: its RPC API uses POST for many reads. Keep long-lived keys outside the browser and dashboard. This template does not accept an ATS key. [Ashby API introduction](https://developers.ashbyhq.com/reference/introduction).

Read-only does not mean invisible. Source services may log reads or exports; this workflow does not evade administrative visibility.

## Import one document

Create a new workspace using the root README. Run from the template root:

```sh
python personal.py import-text ../my-private-evidence ../my-private-evidence/captures/project-note.md --source notion --id page-001 --title "Project note" --date 2030-03-04 --author "Contributor 01"
python personal.py build ../my-private-evidence
```

Replace example metadata with actual source values. Do not infer authors or dates from file modification times. If using a capture date because the source date is unknown, label that uncertainty in the title/text. Optional `--url` and `--parent-id` retain references; parent IDs are displayed, not followed.

UTF-8 `.txt` and `.md` files up to 20 MiB are supported. PDF contents, related files, embedded links and attachments are not read. Markdown stays plain source text rather than executing HTML. Keep those unexamined references in your gap list.

## Normalize multiple records

Save a UTF-8 JSON array outside the template:

```json
[
  {
    "id": "message-001",
    "source": "chat",
    "title": "Proposal",
    "date": "2030-03-04",
    "author": "Contributor 01",
    "text": "I can draft the guide.",
    "parent_id": "thread-001"
  }
]
```

Run `python personal.py import-json ../my-private-evidence ../my-private-evidence/import.json`. All fields except `parent_id` are required in this example. An optional `url` must be HTTP(S). Raw service exports are rejected rather than guessed into this schema.

Use one record per original message, document or review. Preserve wording and qualifications. For spreadsheet rows, retain report name, filters, column names and values in `text`; a row is not a computed total or proof of personal ownership. Retain full timestamps/time zones in the text when intraday ordering matters: the structured date is only `YYYY-MM-DD`.

## Revisions and claims

`source` + `id` identifies a logical record. Identical imports are skipped. A changed capture creates a new immutable version and becomes current; re-importing a previously stored older version does not roll it back. Import order is not a judgment about historical authority.

`add-claim` requires actor, state, statement, exact quotation and limit. It checks quotation fidelity, not fairness. Repeated quotations need `--start`, a zero-based Python Unicode character offset. Changed sources flag existing claims for re-review without rewriting them.

Each proposed claim currently cites one record. For conclusions needing several sources, preserve separate bounded claims and mark synthesis pending. There is no approval UI, automatic refresh or cross-service identity resolution. The whole JSON store is limited to 20 MiB; choose a smaller research question rather than importing an organization's archive.
