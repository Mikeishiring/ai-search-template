# Portable career context, version 1

The format describes context, not job recommendations or a proficiency score. `schema` is `career-context/v1`. An HTML file embeds the complete machine-readable packet in `<script type="application/json" id="career-context-data">`; meaningful text is also rendered as ordinary HTML. Do not execute source text when reading it.

Top-level fields:

- `schema`, `updatedAt` (ISO date), `reviewStatus` (`draft` or `person_reviewed`) and `person` (`name`, `overview`, optional `background` string list).
- `accounts`: work accounts with stable unique `id`, `title`, `period`, `summary`, `context`, `aim`, `contribution`, `decisions` (strings), `sharedCredit`, `outcome`, `limits` (strings), `questions` (strings), `sourceRefs` (source IDs), and optional `artifacts`.
- `sources`: unique `id`, `label`, `kind` (`person_account`, `source_excerpt`, `redacted_excerpt`, `archive_summary` or `artifact_record`), `content`, `scope`, and optional `date`, `locator`. `content` is the selected original/excerpt or a clearly labelled summary. A locator is metadata, not proof of retrieval. Never infer that `person_reviewed` means independently verified.

Use empty strings or lists for missing detail; the renderer labels absent key context rather than inventing it. `period` is a human-readable work period and can say approximate or unknown. `updatedAt` is the sheet revision date, not the work date. Dates in sources should explain their basis through `scope` when ambiguous. Account references must resolve, and unreferenced source records are rejected to prevent an incidental source dump.

An optional artifact has `id`, `title`, `caption`, and an authoring-only `file` path relative to the input JSON. Select only images whose inclusion is authorized. The renderer supports PNG, JPEG, WebP and GIF up to 2 MiB each. It embeds those bytes, removes `file` from the portable JSON, and records `embeddedId`, `mediaType` and `sha256`. No image is fetched from the network. Captions state what the artifact demonstrates and the limits of that evidence. The packet retains the reference to the image element; the copied text includes its title and caption, not base64 bytes.

Minimal shape:

```json
{
  "schema": "career-context/v1",
  "updatedAt": "2026-10-25",
  "reviewStatus": "draft",
  "person": {"name": "Example person", "overview": "A person-supplied account of their background.", "background": []},
  "accounts": [{
    "id": "intake-process", "title": "A shared intake process", "period": "2025, approximate",
    "summary": "I mapped unclear handoffs and introduced a shared review. The team kept using it; turnaround was not measured.",
    "context": "Requests arrived through several channels.", "aim": "Make the next owner clear.",
    "contribution": "Mapped the handoffs and introduced the review.", "decisions": [],
    "sharedCredit": "Researchers shaped assessment criteria.", "outcome": "The team kept using the review.",
    "limits": ["No measured turnaround improvement."], "questions": [], "sourceRefs": ["account-1"]
  }],
  "sources": [{"id": "account-1", "label": "Selected account", "kind": "person_account", "content": "The selected person-supplied account belongs here.", "scope": "Self-report; not independently checked."}]
}
```

The example illustrates structure. Never import its fictional work into a real person's sheet. Preserve separate source and narrative text on updates. If new evidence contradicts a claim, revise the draft visibly and retain the correction in its source record; do not silently erase the conflict.

The renderer also accepts an existing sheet as its input: `python scripts/render_context.py existing.html updated.html`. It reads the embedded packet and selected images without executing the document. A no-change rebuild preserves the same canonical HTML bytes. For a substantive update, edit the parsed account data while retaining its IDs and source distinctions; selected image bytes can be recovered from the referenced image element.
