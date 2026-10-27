# Draft a resume from context

Reuse the supplied target, reference resume, existing work history and preferences. Read a supplied reference through the appropriate host reader. Separate its factual content from its layout and tone: facts become attributed context sources, while presentation preferences go in `referenceNotes`. A job description guides relevance; it is not evidence that the person has its skills.

Draft the resume yourself. Choose section order and emphasis for the person's work: employment, selected projects, campaigns, operating experience, partnerships, or other appropriate headings. Preserve actual titles, employers, dates, qualifications, shared credit and material uncertainty. Do not fabricate education, contact information, proficiency or missing employment periods. A project period is not automatically an employment period. With partial history, deliver an explicitly scoped resume draft and identify the missing information.

Read the current context and fingerprint:

```text
python scripts/render_resume.py career-context.html --inspect
```

Create a private projection with this shape. Every factual entry, including headings and dates, must be supported by its referenced accounts. A personal-history account may carry self-reported employment, education and contact details; keep that attribution in the source packet. Never copy another person's details from a reference template.

```json
{
  "schema": "resume-draft/v1",
  "contextSha256": "exact fingerprint returned by inspect",
  "preparedOn": "2030-09-01",
  "target": null,
  "referenceNotes": "Selected project structure from the supplied reference; no employer or date inferred.",
  "summary": {"text": "A supported introduction.", "accountIds": ["account-id"]},
  "contact": [],
  "sections": [{
    "title": "Selected experience",
    "entries": [{
      "heading": "Supported work or position title",
      "details": "Supported employer and dates, or omit when unknown",
      "bullets": ["A specific contribution and supported result, with shared credit or limitations when material."],
      "accountIds": ["account-id"]
    }]
  }]
}
```

`summary` may be null. `contact` is optional; each supplied contact line uses the same `{text, accountIds}` shape as the summary. `target` is the desired role, not a claim about the person's current title. Keep unknown detail fields empty. Use only the relevant accounts; do not pack the whole archive into a resume.

```text
python scripts/render_resume.py career-context.html resume.json resume.html
```

The renderer rejects stale fingerprints, unknown account IDs, malformed input and accidental overwrites. Use `--force` only for an intended replacement. It produces a separate draft with source disclosures, printable layout and plain-text export. It does not certify the truth of drafted sentences, generate a DOCX, or submit applications. Images remain in the career-context sheet; the resume is readable text.

Compare every resume claim with its accounts and original sources. Review the copyable/printed text itself: essential qualifications and shared ownership must be in that text, not merely in the evidence disclosure that printing omits. Check reference fit, relevance, chronology and unsupported skills. The HTML contains selected private evidence; printing and text download omit that evidence but retain the draft label. Open desktop and mobile layouts, inspect print, test text export and preserve the archive as the canonical source.

Preserve caveats that change a stated claim: prototype, shared ownership, reported result, uncertain date or disputed attribution. Do not add boilerplate about absent metrics when the resume makes no such metric claim. Keep that audit detail in the source archive. A chronology-only entry may use an empty `bullets` list; do not invent duties to fill it. Check printed pagination and remove accidental spill pages without shrinking type below a readable size.
