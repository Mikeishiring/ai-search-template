# Bring an older notebook into the complete document

The default output is one `CAREER-CONTEXT.html` with Work, Career timeline and Interview prep. Do not create a second notebook to add those views. The older notebook renderer remains for explicitly requested legacy reproduction.

## Reconcile saved material

Inventory current context and saved notebooks or preparation before replacing the document. A notebook may contain unique stories, corrected wording, explicit quarters, introduction alternatives and rehearsal notes that the older canonical packet lacks. Browser-only edits are absent until the person saves the HTML; use their latest saved copy when available.

For a notebook with `career-draft-data`, run:

```text
python scripts/merge_notebook.py current-context.html saved-notebook.html merged-context.json
```

Resolve the script relative to the skill. Choose a new private output. It retains existing accounts and capabilities, imports unique accounts, sources and images, maps explicit periods to `timeline`, and prepares a structured interview draft from saved wording. Original narrative, notes and metadata are retained as clearly labelled archive sources. It does not turn a notebook edit into verified evidence.

Inspect the merged packet before building. Reconcile differing accounts and stale claims; preserve later corrections, shared credit, AI assistance and uncertainty. The importer rejects conflicting existing periods or an already-prepared context rather than choosing silently. Complete the draft with [interview preparation](interview-prep.md), choosing useful lead stories and questions for the person's purpose. Keep unknown dates and unsupported outcomes unknown.

Then update the existing private archive:

```text
python scripts/archive_context.py build merged-context.json private-workspace --update
```

Use `render_context.py` directly when there is no database. Keep the established HTML path as the entry point. Do not delete the older source notebook during reconciliation.

## Preserve one packet

`timeline`, `interview` and private `rehearsal` notes live in `career-context/v1` with accounts and sources. Full HTML and JSON downloads retain them; reading filters do not remove them. Ordinary updates re-render that complete packet, not an earlier work-only input. Refresh interview preparation when its evidence fingerprint changes.

Verify original account and source text, image hashes, all periods, opening alternatives and practice notes. Follow a period into its work and prepared story; test back/forward, direct links, rehearsal notes, download/reopen, print and no-JavaScript reading. The visual design can change without discarding a view or its evidence.
