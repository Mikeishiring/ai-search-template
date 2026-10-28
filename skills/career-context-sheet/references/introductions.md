# Choose an introduction before polishing it

Help the person recognise a faithful account of their career before repeatedly revising one draft. Reuse their known background, intended reader and purpose. An open destination is valid; do not invent a target title or employer.

For the first About Me review, draft five or six complete alternatives. Change the organising idea and evidence emphasis. Useful angles might include depth in a craft, wider responsibility, progression, independent work or a supported next direction. Choose the angles for this person: they are not fixed career categories or a ladder of increasingly senior titles. Early-career, specialist, management, returning and changing-career contexts need different choices. Keep demonstrated experience separate from ambition.

Use comparable lengths suited to the intended use. Each version should establish who the person is, make their contribution tangible and point toward relevant work. Write naturally and professionally, without conversational filler or inflated executive language. Preserve the same factual boundaries across versions, including shared credit and material uncertainty. Keep sources accessible through the underlying accounts rather than repeating inventories beneath each introduction. If the context cannot support meaningful alternatives, gather the consequential missing account instead of filling six slots with invented differences.

Open the comparison as the first review destination. Number the options, label their emphasis and show their full wording. Ask which sounds most like the person and what they would keep or drop. Explain trade-offs candidly. Do not automatically select, combine or replace an introduction. Retain the alternatives, source basis and explicit feedback in private continuation context. Reuse them on return; a wording preference does not confirm a new fact, capability or career goal.

## Deliver the comparison

The host agent writes the options; static HTML does not generate them. The [notebook renderer](notebook.md) accepts an optional private JSON list:

```json
[
  {
    "id": "craft",
    "title": "Depth in the work",
    "text": "The full proposed introduction, grounded in this person's accounts.",
    "sourceRefs": ["an-included-source-id"]
  }
]
```

This illustrates the shape, not reusable wording. Supply five or six options for a full first review. The renderer accepts one to six to preserve smaller author-selected sets. IDs must be unique; titles and text must be nonempty. Optional sourceRefs must resolve to sources in the canonical packet. Structural validation does not prove factual support.

```text
python scripts/render_notebook.py career-context.html career-notebook.html --introductions introductions.json
```

Open the output with `?person=own&view=overview&compare=intros`. The overview also has a Compare introductions control. Copying and comparing do not change the current introduction. Private HTML, its reading fallback and copied coach context retain the alternatives. The selected public portfolio excludes them.

Use the latest downloaded notebook as input when revising an existing comparison, so saved edits survive. Supplying different options creates a new browser-storage identity; download browser-only edits before generating that revision. Reopening without new input preserves the existing options and identity. Apply the person's chosen text only when requested, preserving the other options for reference.

The simpler career-context sheet and interview brief support a single overview or opening. Conduct the comparison in a notebook or the conversation before rendering the chosen text there. Do not put notebook fields into career-context/v1 or interview-preparation/v1. Keep any interim opening clearly proposed and preserve already-written text while the choice is open.
