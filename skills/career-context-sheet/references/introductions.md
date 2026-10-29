# Choose an introduction before polishing it

Help the person recognise a faithful account of their career before repeatedly revising one draft. Reuse their known background, intended reader and purpose. An open destination is valid; do not invent a target title or employer.

For the first About Me review, draft five or six complete alternatives. Change the organising idea and evidence emphasis. Useful angles might include depth in a craft, wider responsibility, progression, independent work or a supported next direction. Choose the angles for this person: they are not fixed career categories or a ladder of increasingly senior titles. Early-career, specialist, management, returning and changing-career contexts need different choices. Keep demonstrated experience separate from ambition.

Use comparable lengths suited to the intended use. Each version should establish who the person is, make their contribution tangible and point toward relevant work. Write naturally and professionally, without conversational filler or inflated executive language. Preserve the same factual boundaries across versions, including shared credit and material uncertainty. Keep sources accessible through the underlying accounts rather than repeating inventories beneath each introduction. If the context cannot support meaningful alternatives, gather the consequential missing account instead of filling six slots with invented differences.

Open the comparison as the first review destination. Number the options, label their emphasis and show their full wording. Ask which sounds most like the person and what they would keep or drop. Explain trade-offs candidly. Do not automatically select, combine or replace an introduction. Retain the alternatives, source basis and explicit feedback in private continuation context. Reuse them on return; a wording preference does not confirm a new fact, capability or career goal.

## Deliver the comparison

The host agent writes the options; static HTML does not generate them. Keep the comparison inside the complete document as `interview.introOptions`:

```json
[
  {
    "title": "Depth in the work",
    "text": "The full proposed introduction, grounded in this person's accounts."
  }
]
```

This illustrates the shape, not reusable wording. Supply five or six supported options for a full first review; retain a smaller existing set when appropriate. Keep their evidence in the underlying accounts. Structural validation does not prove factual support.

Re-render the complete packet with `render_context.py`, or update its existing archive. In Interview prep, open **Alternative openings** beneath the retained opening. Comparing does not change the current introduction. Full HTML, JSON and complete copied preparation retain the options.

Use the latest complete saved document when revising a comparison so rehearsal notes and all other views survive. Apply the person's chosen wording only when requested, preserving the other options for reference. Keep the current opening while the choice is unresolved. Older notebook comparisons should be reconciled through [the migration guide](notebook.md), not maintained as a second version.
