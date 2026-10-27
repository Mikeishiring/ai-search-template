# Adaptive workflow review

26 October 2026. Local validation using fictional inputs; no live personal accounts were collected or published.

The previous release preserved work accounts, but did not complete the requested journey. Its standalone skill had no local database or executable resume path. Role adaptation depended on the agent improvising, and visuals were hidden inside a text disclosure.

## Critique and repairs

| Finding | Repair | Evidence |
|---|---|---|
| No standalone database | SQLite stores selected accounts, sources, links, images, coverage and revisions; search and recovery work without the repository | Extracted-skill journeys in [adaptive tests](../tests/test_adaptive_workflow.py) |
| Resume creation was only a promise | A reference-aware projection and renderer produce a populated private resume with source review, print/PDF and text export; stale context is rejected | Adaptive tests and [resume browser checks](../tests/check_resume.cjs) |
| No explicit role adaptation | Discovery guidance covers hiring, engineering, operations, growth, marketing, BD and hybrid work; free-text profile and themes travel with the context | [Adaptation guide](../skills/career-context-sheet/references/adaptation-and-discovery.md), six independent raw-note agent trials |
| Visuals were difficult to find or read | Relevant images appear with the account; an enlargement dialog supports small-screen inspection | [Sheet browser checks](../tests/check_sheet.cjs), a fictional diagram with disclosed reconstruction |
| Image paths escaped the selected folder; embedded hashes were ignored | Relative contained paths, saved-checksum verification and aggregate output-size limits | Adversarial image tests and round-trip tests |
| Failed first database setup blocked recovery | Failed initialization closes and removes only its newly created incomplete database; a new build can retry | Injected schema-write failure regression |
| Mobile profile labels overflowed; print lost fictional labels | Wrapping and print-specific state labels | Independent 320px and print-media checks |
| Default file creation failed in the Windows sandbox | Atomic no-clobber rename on Windows; exclusive hard links on POSIX | Race-preservation tests; six successful default-save retries in the normal Windows sandbox |
| Single-account drafts repeated the introduction | Scope/role overview guidance keeps the narrative in the account | Independent revised six-role drafts |

The review was independent and read-only. Confirmed findings were reproduced and repaired. The raw-note trials were authored independently of the prewritten test packets; neither test type proves universal model quality.

## Checks

- `python -m unittest discover -s tests -q`: 135 passing toolkit tests.
- `python -m unittest discover -s ai-search-mvp/tests -q`: 87 passing research regressions.
- `python tools/check_mcp.py`: offline handshake and six-tool contract passed; no model or real source called.
- `python tools/check_multisource.py`: selected-window/follow-up strategy recovered all 13 in-scope fictional records, with no out-of-scope reads. One task remained blocked; retrieval is not semantic completeness.
- Six independent raw-note trials produced role-appropriate context, SQLite archives and resumes; search and byte-identical recovery passed. After the Windows repair, all six default saves worked without replacement flags.
- Independent trials passed 48 context/resume layout checks across 320, 375, 768 and 1440px. Separate browser checks covered a real embedded test image, enlargement, copy fallback, keyboard access, downloads, saved-file reopening, print, reduced motion and no-JavaScript reading. No external requests or browser errors were observed.

## Remaining limits

The host agent discovers and reads authorized connectors or selected files. The skill does not connect accounts, import every vendor's raw export, refresh automatically or guarantee “all context.” The collection map records actual scope and missing access. These trials used supplied fictional notes; live connector ingestion, original visual retrieval, large real career histories and cross-model equivalence remain untested.

Drafted resume sentences still need a semantic comparison with their sources. Reference checks establish structure and freshness, not factual truth. SQLite is unencrypted and retains old revisions; the HTML contains selected private evidence. See [privacy](PRIVACY.md) and [archive retention](../skills/career-context-sheet/references/local-archive.md).

## 27 October revision

The next critique found weak editorial selection, repetitive visible detail, unclear private exports and missing mobile navigation. The sheet now leads with concise connected accounts, keeps full fields in accessible disclosures, offers all-account or single-account text copying with source excerpts excluded by default, and retains a mobile index without JavaScript. Full HTML/JSON remain explicitly private. Optional sibling links connect separately delivered resumes and database files. Resume copy feedback appears beside its controls; chronology entries do not require invented bullets.

The workflow now begins with purpose and responsibilities before platform discovery, checks coverage across periods and less documented work, and records selection reasons. Its six discipline examples are explicitly non-exhaustive. A further cold synthetic hybrid trial began with raw theatre work, repair, booking, routine-check and rejected-proposal material plus another person's reference CV. It produced a broad archive and two differently targeted resumes from one unchanged evidence fingerprint. It retained contractor credit, a cancellation, sparse dates and unfinished work, and excluded the reference owner's qualifications. The review caught unnecessary metric disclaimers and a shortened phrase that lost the qualifier “some”; both were repaired.

Current checks: 136 toolkit tests and 87 research tests passed; MCP/multisource checks passed; public and private rendered checks covered 320, 375, 768 and 1440 pixels, copying, fallback, downloads, mobile navigation and no-script reading. The new cold trial added 12 layout checks and two visually reviewed one-page PDFs. These establish bounded behavior, not universal adaptation, exhaustive context collection or automatic factual validation. Every new person's synthesis still needs evidence review.
