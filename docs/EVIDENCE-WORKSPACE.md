# Keep a local evidence workspace

Use this optional workflow for immutable source captures and proposed claims linked to exact quotations. It is separate from the portable career-context sheet. Importing records does not automatically write a career account.

From the project root, with Python 3.11 or later:

```sh
python personal.py init ../my-evidence --title "My work evidence" --synthetic
python personal.py import-json ../my-evidence examples/first-records.json
python personal.py add-claim ../my-evidence --source chat --id proposal-01 --actor "Contributor 01" --state offered --statement "Contributor 01 offered to draft a troubleshooting guide." --quote "I can draft a troubleshooting guide for the support team." --limits "This proposal does not establish delivery or adoption."
python personal.py build ../my-evidence
```

Open `../my-evidence/DASHBOARD.html`. These commands create two fictional records and one proposed claim. Expand a source to read its original text. The counts describe this tutorial's supplied records, not your career.

For real material, create a different workspace without `--synthetic`. Follow [Source preparation](SOURCES.md) to import selected text files or normalized JSON. Run `build` after changes. Repeated identical imports are skipped; changed captures preserve previous versions and flag existing claims for re-review.

`add-claim` checks the exact quotation. It does not establish fair attribution or verify meaning. Each claim currently cites one record. There is no approval UI, automatic synthesis or source-account connection.

Keep this workspace and its dashboard outside the public checkout. The HTML embeds imported text. [Privacy guide](PRIVACY.md).
