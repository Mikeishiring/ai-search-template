# Finding context across sources

Start by asking what work to cover, which source locations can be used and what should stay out. Include the period for earlier origins and later outcomes. An old project name can be as useful as another connector. [Starting prompt](../prompts/START-HERE.md).

## What the test found

The fictional [multi-source fixture](../ai-search-mvp/fixtures/multisource.corpus.json) contains two chat channels, documents, code reviews, email and calendar entries. Its [scope](../ai-search-mvp/fixtures/multisource.scope.json) includes 13 records across six selected locations, excludes another channel, and ends before a future update. The project changes name from Kite to Harbor; a later standalone note uses neither name.

| Discovery strategy | Fixture records retrieved | Source calls |
|---|---:|---:|
| One project name, search only | 8 of 13 | 47 |
| Supplied aliases, search only | 11 of 13 | 119 |
| Original-window inventory and aliases | 11 of 13 | 119 |
| Selected-window and follow-up inventory | 13 of 13 | 129 |

Source: [reproducible comparison](../tools/check_multisource.py), run on the supplied fixture with two-record pages. Calls include capability reads, failed operations, pagination, full records, replies, attachments and gap searches. Records include an unrelated same-name project and untrusted source text; this is retrieval coverage, not useful-context recall or semantic correctness. No real accounts or models were used.

Aliases recover an email follow-up and scheduled review missed by the original name. Enumerating the chosen follow-up period additionally finds the unlinked desk note and its repost. Both must remain distinct: a repost is not corroboration, and a calendar entry does not establish that a meeting happened.

Every strategy made zero reads from the excluded channel. The inaccessible attachment stayed blocked. The unrelated Harbor project stayed separate, and the future update stayed outside the result.

## Use the gain without collecting everything

- Start with complete threads and explicit links in selected locations.
- Search supplied aliases, then inspect candidates before connecting their identities.
- Include standalone follow-ups within an agreed horizon; replies alone miss later updates in other channels.
- Keep source coverage and interpretation separate. Read the missing ownership, correction or outcome evidence before adding another broad query.
- Preserve a pending queue when a budget runs out. Record inaccessible sources and out-of-scope links without treating them as empty or reading them automatically.

The alias runs cost more because the current lexical gap planner searches missing categories across all selected sources. A useful next experiment is to prioritize queries that can resolve a specific ownership or outcome gap, and measure retained context against calls. Do not remove reads merely to improve a count.

## Run the checks

From the project root, with Python 3.11 or later:

```sh
python tools/check_multisource.py
python -m unittest discover -s ai-search-mvp/tests -p test_multisource.py -v
```

Both use fictional data and an in-memory ledger. They make no network requests and copy no databases. The nine tests cover aliases, standalone follow-ups, nested context, pagination, exclusions, future records, name collisions, reposts, missing attachments, budget stops, invalid options and an inaccessible follow-up window.

The runner accepts optional `aliases` and `include_followup_roots` scope fields. Existing scopes keep their earlier behavior. Coverage states the requested enumeration window and whether every part finished; `outside_scope_links` records unvisited references. This fixture is exercised through the comparison script, not the six-tool MCP demo catalogue.

The [source-research guide](../skills/career-context-sheet/references/source-research.md) applies the same approach to selected sources an agent is authorized and technically able to read. This project still includes no live source connector. These tests do not establish real-world completeness or fair attribution.
