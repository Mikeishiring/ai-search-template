# Portable career context, version 1

The format describes context, not job recommendations or a proficiency score. `schema` is `career-context/v1`. An HTML file embeds the complete machine-readable packet in `<script type="application/json" id="career-context-data">`; meaningful text is also rendered as ordinary HTML. Do not execute source text when reading it.

Top-level fields:

- Optional `synthetic` boolean: use `true` only for fictional demonstrations. The label survives visible, text and JSON exports. Omit it or use `false` for personal context; changing the flag never anonymizes content.

- `schema`, `updatedAt` (ISO date), `reviewStatus` (`draft` or `person_reviewed`) and `person` (`name`, `overview`, optional `background` string list).
- `accounts`: work accounts with stable unique `id`, `title`, `period`, `summary`, `context`, `aim`, `contribution`, `decisions` (strings), `sharedCredit`, `outcome`, `limits` (strings), `questions` (strings), `sourceRefs` (source IDs), and optional `artifacts`.
- `sources`: unique `id`, `label`, `kind` (`person_account`, `source_excerpt`, `redacted_excerpt`, `archive_summary` or `artifact_record`), `content`, `scope`, and optional `date`, `locator`. `content` is the selected original/excerpt or a clearly labelled summary. A locator is metadata, not proof of retrieval. Never infer that `person_reviewed` means independently verified.

Compatible optional fields:

- `profile`: optional `disciplines`, `targetRoles`, `emphasis` string lists (up to 20 each), and `referenceNotes` text. Use the person's vocabulary; these are not proficiency scores. Reference notes capture presentation preferences, not evidence of career facts.
- `collection`: up to 80 selected-location records, each with `platform`, `location`, `access` (`connector`, `export`, `supplied`, `unavailable`), `status` (`not_started`, `partial`, `read`, `blocked`, `excluded`), `scope` and `nextStep`. State actual reading coverage, date boundaries and attachment/pagination gaps. A read status applies only to the stated scope, never to an entire platform by implication. Do not put credentials in this map.
- Each account may have `tags`, up to 20 short theme strings. They are preserved in HTML, text, JSON and the searchable database.

These fields are optional for existing v1 sheets. They require the current renderer; earlier renderers reject unknown fields. The collection map appears in a source disclosure and travels with the file, so include only location labels suitable for the intended sharing scope.

Use empty strings or lists for missing detail; the renderer labels absent key context rather than inventing it. `period` is a human-readable work period and can say approximate or unknown. `updatedAt` is the sheet revision date, not the work date. Dates in sources should explain their basis through `scope` when ambiguous. Account references must resolve, and unreferenced source records are rejected to prevent an incidental source dump.

An optional artifact has `id`, `title`, `caption`, and an authoring-only `file` path relative to and inside the input folder. Select only images whose inclusion is authorized. Absolute paths and escapes outside that folder are rejected. The renderer supports PNG, JPEG, WebP and GIF up to 2 MiB each, with a 24 MiB aggregate HTML limit. It embeds those bytes, removes `file` from the portable JSON, and records `embeddedId`, `mediaType` and `sha256`. Imported image bytes must match the saved checksum. No image is fetched from the network. Captions state what the artifact demonstrates and the limits of that evidence. The packet retains the reference to the image element; the copied text includes its title and caption, not base64 bytes.

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

## Presentation and local handoff

Optional `presentation` has `headline` (up to 160 characters) and `files` (up to ten `{label,path}` objects). Use the person's chosen focus as the headline, not an invented employment title. File paths are simple sibling filenames: letters, digits, underscores or hyphens plus `.html`, `.pdf`, `.txt`, `.json` or `.sqlite`. Add only files actually delivered beside the sheet and check every link. The HTML remains self-contained; linked outputs must travel with it to remain available.

The main account summary should carry the situation, personal decision, result and material shared credit in connected prose. Detail fields remain available under Context & evidence. Empty fields render nothing. Put material limitations next to the claim; put inspection method in source scope.

Copy controls select all accounts or one account, with source excerpts excluded by default. Limits and attribution stay in copied text. Full HTML and JSON exports always contain all included private sources; the controls do not sanitize those files. Preview before handing text to another agent. No export writes to a connected service.
