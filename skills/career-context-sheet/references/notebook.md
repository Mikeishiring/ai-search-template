# A notebook from existing career context

Use the notebook when the person wants to read connected work accounts, follow an explicit quarterly arc, practise a story and add a missing detail. The existing [sheet](format.md) remains the canonical evidence packet. The notebook adds an editable presentation; it does not require a new research process or a new source connection.

## Render

```text
python scripts/render_notebook.py context.json career-notebook.html
python scripts/render_notebook.py context.json career-notebook.html --quarters quarters.json
python scripts/render_notebook.py existing-notebook.html refreshed-notebook.html
```

Resolve the script relative to this skill. Python 3.11 or later and the standard library are sufficient. The renderer accepts `career-context/v1` JSON or an HTML file containing that packet. Replacing an existing output requires `--force`.

The output contains the complete canonical packet, the notebook working draft and selected image bytes. The bundled example and runtime work offline; optional linked films and external sources need internet access. Accounts, source records, images and explicit quarters also remain readable as ordinary HTML without JavaScript.

## Two retained layers

| Layer | Purpose | Updating it |
|---|---|---|
| `career-context-data`, schema `career-context/v1` | Canonical accounts, source distinctions, review state and image references | Revise the source packet deliberately, retaining IDs and evidence |
| `career-draft-data`, schema `career-notebook/v1` | Editable reading, follow-up answers and presentation choices | Notebook controls save this working layer; download the HTML to retain it |

Notebook edits do **not** silently update the canonical packet. Reimporting a downloaded notebook preserves both layers, including the saved edits. The canonical packet remains available to existing sheet and interview tools; those tools will not automatically consume unreconciled notebook corrections. Before preparing a new interview from corrected material, have the agent reconcile the relevant correction into the canonical account and its supporting record.

The renderer derives a deterministic notebook ID from the canonical packet. Identical context produces the same ID. Changed canonical context produces a new ID, preventing a browser draft for older context from silently replacing a new release. An imported notebook keeps its existing ID and saved working layer. Browser-only changes are not present in a file until it is downloaded.

The first artifact appears as the account's main image; remaining artifacts are retained as additional private images. Every canonical artifact keeps its bytes, caption and hash. Public sharing choices are separate from preservation: an unselected image or source is still present in the private notebook. Inspect the complete embedded file before sharing it.

## Explicit quarterly companion

Quarters are authored summaries supported by selected evidence. Never derive them from the sheet revision date, source capture date or an uncertain work period. If quarterly evidence is unavailable, leave the companion out and use the work accounts.

```json
{
  "schema": "career-quarters/v1",
  "synthetic": true,
  "quarters": [{
    "id": "2030-Q1",
    "period": "2030 Q1",
    "title": "Clarifying a shared handoff",
    "focus": "Agree who owns the next step.",
    "actions": ["Mapped the recurring handoffs."],
    "tension": "The next owner was unclear.",
    "style": "Made responsibilities explicit during a small trial.",
    "questions": ["Which parts remained in use?"],
    "sourceRefs": ["account-1"],
    "accountId": "intake-process"
  }]
}
```

This is a fictional structure example; the IDs must resolve in the actual context packet. Each quarter requires every illustrated field; empty text or an empty actions/questions list is valid. Quarter IDs are unique `YYYY-Q1` through `YYYY-Q4` values. The period must match the ID. `sourceRefs` must contain unique references to included sources, and `accountId` links to an included work account. The optional `synthetic` boolean must match the context packet when supplied.

Keep quarters in the intended reading order. A linked account may span more than one quarter; its complete work period remains intact. Pressure, a change in approach and independent use require supporting evidence. An empty field is better than inventing a struggle, decision or result.

The companion is embedded separately as `career-quarters-data`. HTML reimport preserves it. Supplying a new `--quarters` companion explicitly replaces the notebook's quarterly presentation while preserving other notebook edits.

## Check the result

Read one account, inspect its original context, add a meaningful missing detail and read the revised account. Follow one quarter into its linked work account and back. Check shared credit and uncertainty at both ends.

Before handoff, compare the canonical packet and notebook draft, including sources and all selected images. Exercise navigation, keyboard focus, source readers, image readers, downloads and reopening. Check a narrow screen, long content and JavaScript-disabled reading. Static validation establishes data preservation; it does not establish visual quality or usability.
