# Contributing to Career Context AI

Keep the first-use path small: one account, one portable sheet, understandable source boundaries. Preserve old commands and the `career-context/v1` format when making compatible improvements.

Use fictional examples in issues, screenshots and pull requests. Never attach a real career sheet, source export, credential, private URL or model session log to this public repository.

## Local checks

Python 3.11 or later and the standard library are sufficient:

```sh
python -m unittest discover -s tests -q
python -m unittest discover -s ai-search-mvp/tests -q
python tools/check_mcp.py
python tools/check_multisource.py
python tools/build_demo.py
python tools/check_release.py
```

The historical report also has a Node.js interaction check:

```sh
node ai-search-mvp/tests/check_report.cjs
```

For sheet changes, exercise copying and its fallback, source links, keyboard disclosures, downloads and saved-file reopening. Check 320, 375, 768 and 1440 pixel widths, long content, reduced motion and JavaScript disabled. Meaningful text must remain readable offline. The preview image must come from the fictional example.

With Playwright available, `node tests/check_sheet.cjs` exercises that path and writes a receipt and screenshots to a temporary folder. Set `CAREER_CONTEXT_QA_DIR` to keep them in a chosen directory. `PLAYWRIGHT_CHANNEL=msedge` selects installed Edge; otherwise the check uses Playwright's Chromium. These are optional development dependencies, not requirements for using a sheet.

## Publication review

`tools/check_release.py` checks file patterns, relative links and exact manifest hashes. It is additional screening, not proof that text is anonymous. Review the diff and all embedded data before refreshing the manifest:

```sh
python tools/check_release.py --write-manifest
python tools/check_release.py
```

Only `docs/career-context-preview.png` is allowed as a binary release asset; it must be the reviewed fictional screenshot. Other binaries are refused. Personal workspaces and hidden session data do not belong in a release.

For a pull request, describe the user-visible change, the checks run and any remaining limits. Preserve draft/review state, source distinctions, dates, ownership and unknowns in every export.
