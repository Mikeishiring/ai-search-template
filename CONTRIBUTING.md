# Contributing to Career Context AI

Follow the [product contract](docs/PRODUCT.md). Keep the first-use path small: one account, one portable sheet, understandable source boundaries. Preserve old commands and the `career-context/v1` format when making compatible improvements.

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
python tools/build_skill.py ../career-context-sheet.zip
```

The historical report also has a Node.js interaction check:

```sh
node ai-search-mvp/tests/check_report.cjs
```

For sheet changes, exercise copying and its fallback, source links, keyboard disclosures, downloads and saved-file reopening. Check 320, 375, 768 and 1440 pixel widths, long content, reduced motion and JavaScript disabled. Meaningful text must remain readable offline. The preview image must come from the fictional example.

With Playwright available, `node tests/check_sheet.cjs` exercises that path and writes a receipt and screenshots to a temporary folder. Set `CAREER_CONTEXT_QA_DIR` to keep them in a chosen directory; `CAREER_CONTEXT_HTML` selects another fictional sheet with at least one account and source reference to check. `PLAYWRIGHT_CHANNEL=msedge` selects installed Edge; otherwise the check uses Playwright's Chromium. These are optional development dependencies, not requirements for using a sheet.

For interview changes, render `examples/career-context.json` with `examples/interview-preparation.json` using the bundled interview renderer. Set `CAREER_INTERVIEW_HTML` to the resulting HTML and run `node tests/check_interview.cjs`. It uses the same QA directory and browser options and checks all six populated sections, source fidelity, navigation, copy fallback, independent reopening, no-JavaScript reading, print and mobile layout.

## Publication review

`tools/check_release.py` checks file patterns, relative links and exact manifest hashes. It is additional screening, not proof that text is anonymous. Review the diff and all embedded data before refreshing the manifest:

```sh
python tools/check_release.py --write-manifest
python tools/check_release.py
```

Only `docs/career-context-preview.png` is allowed as a binary release asset; it must be the reviewed fictional screenshot. Other binaries are refused. Personal workspaces and hidden session data do not belong in a release.

Screen every outgoing commit's contact metadata before publishing, using the actual destination branch as the range base:

```sh
python tools/check_git_privacy.py origin/main..HEAD
```

Use `HEAD` to audit all reachable history. The check reports hashes and fields without echoing rejected addresses. It permits GitHub noreply identities only and checks author, committer and message/trailer addresses. It does not inspect annotated tags or remove existing remote history.

Enable GitHub's private-email setting for web-created merges as well; a local commit check cannot control GitHub's merge author identity. Do not rewrite published history or force-push as an automatic repair. Prepare exact ref changes, preserve file trees, and obtain authorization first.

For a pull request, describe the user-visible change, the checks run and any remaining limits. Preserve draft/review state, source distinctions, dates, ownership and unknowns in every export.


## Standalone distribution

The shareable ZIP contains the skill instructions, references, sheet/interview/notebook renderers and HTML templates, host metadata and license. The builder names each input explicitly; it does not recurse through a workspace. Tests extract it into an unrelated folder and run isolated Python against it, including update and failure paths.

Do not add account configuration, source exports, test transcripts or a runtime dependency to this bundle. Keep optional local research tooling in the full repository. Changes to public input/output behavior must preserve the format and selected personal context.

The Product checks workflow runs toolkit and research tests, offline MCP checks, example reproducibility, publication checks and a bundle build on Windows, macOS and Linux with Python 3.11, plus Linux with Python 3.14. It uses read-only repository permissions and does not publish. A configured workflow is not a passing run: inspect results on the actual release revision.

Before sharing a release, review the diff and embedded data, refresh the publication manifest, run the checks above, and exercise the rendered sheet. Run a fresh host trial after changing research instructions; preserve the first result and judge attribution, decisions, counterevidence and corrections rather than source count alone.

Notebook changes also rebuild `CAREER-NOTEBOOK.html` through `tools/build_demo.py`. The optional renderer, template and notebook reference are named explicitly in the standalone bundle. Test both a sparse account and the fictional quarterly companion; inspect source access, native-dialog menu, image readers and the responsibility follow-up.

Run `node tests/check_notebook.cjs` for the shipped notebook route, menu and source handlers. The Python suite also runs it when Node.js is installed and checks that the notebook rebuild is identical. Node.js 18+ is a development check only; the exported notebook needs a browser, not Node.js.
