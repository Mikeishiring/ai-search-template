# Local context and SQLite

Use a private workspace outside the skill and any public checkout. The agent prepares the input JSON; the person should not need to write schemas or run commands. The same Python 3.11+ standard-library path works in the extracted skill.

```text
python scripts/archive_context.py build context.json my-context
python scripts/archive_context.py search my-context/career.sqlite "handoff"
```

`my-context/CAREER-CONTEXT.html` is the reading entry point. `career.sqlite` stores normalized accounts, sources, account/source links, selected image bytes, source coverage and complete revisions. Search returns up to 50 matching current accounts/sources. It uses literal substring matching, not semantic ranking. Images and tags survive updates; raw unselected exports are not copied.

When facts change, update the selected context, preserve account/source IDs and correction evidence, and run:

```text
python scripts/archive_context.py build corrected.json my-context --update
```

Identical input adds no revision. Changed content retains a historical revision in the same database; it does not create another database. A different person's name is rejected to prevent mixing archives. An independently edited HTML file is preserved: import it into a new workspace or reconcile it before updating. Source facts are never automatically refreshed from connected services.

Recover a portable sheet without the original files:

```text
python scripts/archive_context.py export my-context/career.sqlite recovered.html
python scripts/archive_context.py export my-context/career.sqlite previous.html --revision EXACT_REVISION_HASH
```

Revision IDs are returned by `build` and stored in `revisions.id`. Exports refuse existing output paths. Keep the database private: it is not encrypted, it contains selected source text and historical revisions, and deleting an account from the current sheet does not delete it from history. To make a deliberately reduced archive, build a new private database from the reduced current packet and use the person's normal secure deletion process for the old one. Do not present this as automatic redaction or erasure.

The optional full-repository research server remains useful for large selected exports and resumable investigations. It is not required to build, search, update or recover this SQLite archive. Discovery and collection are performed by the host agent; these scripts perform no connector or model calls.
