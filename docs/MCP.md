# Connect an AI host to the fictional demo

The bundled MCP server supplies **synthetic fixtures only**. It does not authenticate to Slack, Notion, GitHub or an ATS. It does not read `personal.py` workspaces. Connecting it to an AI host is not the same as connecting real source accounts.

## Check the server without an AI model

From the repository root:

```sh
python tools/check_mcp.py
```

Expect `stdio_handshake: passed`, `tools: 6`, `synthetic_inventory: passed`, `model_called: false` and `real_sources_connected: false`. This launches the server, lists tools and reads fictional inventory. It does not verify your AI host's configuration or authorize external data access.

## Add a local stdio server in your host

Your AI host must support local stdio MCP servers. Find your Python executable with `python -c "import sys; print(sys.executable)"`. Use its absolute path and the absolute path to `ai-search-mvp/mcp_server.py`.

Illustrative settings—translate the surrounding configuration keys to your host's format:

```json
{
  "mcpServers": {
    "synthetic_research": {
      "command": "<absolute path to Python>",
      "args": ["<absolute path to ai-search-mvp/mcp_server.py>"]
    }
  }
}
```

Do not paste literal angle-bracket placeholders. The process uses stdin/stdout for JSON-RPC. Starting it in a terminal and seeing it wait silently is normal, not an account login screen. Do not put debugging text on protocol stdout.

Restart/reconnect the server through your host and confirm the six tools are visible. Ask it to call `source_inventory` with `{"case":"training"}`. Every tool needs `case`; accepted values are `training`, `challenge`, `search_only` and `semantic`.

Only after that succeeds, provide [the synthetic research prompt](../ai-search-mvp/RESEARCH-PROMPT.md) and select the case. `research_run` writes a local synthetic ledger; source operations do not mutate online systems. The model host may send synthetic passages to its inference provider. Model usage and charges belong to that host, not this server.

## Turn selected context into a portable sheet

The companion [career-context skill](../skills/career-context-sheet/SKILL.md) guides the output: one readable HTML sheet with embedded structured context for the person's agents. Use selected accounts and sources, preserve contribution and shared credit, distinguish summaries from original excerpts, and carry unknowns into the exported text. Do not turn a request to capture context into unsolicited career advice.

The skill can work with pasted accounts, local files or selected context returned by an authorized connector. This bundled MCP still serves fictional fixtures only. Installing the skill does not add real-source access, expose personal workspaces or save a hosted profile. Any connector's selected-source and confirmation boundaries still apply.

Try the fictional sheet using the [README walkthrough](../README.md#make-a-portable-career-context-sheet). Keep a real person's packet and generated HTML outside this public template.

## Important gaps

- `review_submit` saves proposals to `ai-search-mvp/runs/<case>/model-reviews.json`. The historical report currently does **not** render these new submissions. A successful submit is not a refreshed dashboard. Inspect that JSON directly; integration is unfinished.
- The historical autonomous experiments use a different, richer server/tool contract. Their prompts cannot simply be pasted into the six-tool demo bridge. They are recorded experiments, not the novice setup path.
- Personal workspaces have no MCP exposure or automated reviewer. Use the local importer and claim command, or deliberately supply selected records to your chosen host; this repository does not silently bridge them.
- A green handshake proves transport, not model understanding, source access or privacy configuration. If tools are absent, stop and diagnose the host connection rather than claiming research happened.

For real source connectors, use [Sources](SOURCES.md) and the proposed contract in [SPEC.md](../SPEC.md). Credentials belong outside prompts, source records and generated HTML.
