# Your context, in your own local folder

Start by choosing what work to cover, exactly which locations may be used, and what may be kept or sent to an AI host. These choices are saved as an enforced policy beside your local captures and career sheet.

```sh
python career_context.py start ../my-career-context
```

The setup asks for the person and work question, dates for earlier origins and later outcomes, selected locations, exact local export files, and privacy choices. It creates `CAREER-CONTEXT.html` in the chosen folder. The initial sheet is empty; setup does not invent a story or connect an account.

## Choose the boundaries first

| Choice | Enforced behavior |
|---|---|
| Exact location IDs | Only selected channel, folder, conversation or repository IDs are admitted. No wildcard or automatic expansion through links. |
| Direct messages | Off by default. Turning on DM access still requires selecting each permitted conversation. |
| Private channels | Off by default; each permitted channel must also be selected. |
| Attachments | Off by default. When enabled, only attachment text already in the selected export and referenced by admitted records is retained. No URL or filesystem attachment fetch. |
| Dates | Records before the agreed earliest origin or after the follow-up horizon are excluded. |
| Local retention | Choose whether to keep selected source text or metadata only. Metadata-only workspaces cannot serve evidence text for research. |
| Model processing | Off by default. `local_only` blocks the research server. `selected_sources` permits an AI host you connect to receive selected text. |

The file picker is currently a terminal path prompt. Source locations come from your exports; there is no live connector discovery or account-login screen. The importer relies on correct location and privacy metadata in the export. It does not independently verify service membership or access rights.

## Capture selected material locally

Normalize an export with the shape in the fictional [selected-export example](../examples/selected-export.json). Each record needs a stable ID prefixed by `chat:`, `docs:` or `repo:`, exact `container`, explicit `kind`, original date, author, title, body, parent and links. `docs` is the local document group and can contain separately selected email or calendar locations. Kinds are `channel`, `private_channel`, `dm`, `document`, `repository`, `email` or `calendar`.

```sh
python career_context.py local-import ../my-career-context ../selected-export.json
python career_context.py local-status ../my-career-context
```

Only files selected at setup can be opened by this command. Import parses that selected file locally, then excludes records outside the policy before saving any capture or exposing it to research. Excluded bodies are not stored or sent to a model. Unknown privacy kinds fail closed. Embedded links never grant additional access.

Your folder contains the policy, admitted captures, research journal when used, depth checklist and one obvious `CAREER-CONTEXT.html`. Nothing is uploaded by setup, import, status or rendering. The local folder is not encrypted; choose a location that matches your backup and synchronization preferences. Its default `.gitignore` excludes everything from accidental Git addition, but does not control cloud-sync software.

For scripted setup, copy the fictional [policy](../examples/local-policy.json) and export outside this public checkout, replace their content with your own selections, and run:

```sh
python career_context.py start ../my-career-context --policy ../my-inputs/local-policy.json
```

Relative export paths resolve beside the policy file. The retention choice is explicit in that file; changing a synthetic label never anonymizes real data.

## Research inside those boundaries

An AI host can use the local research server only when `model_processing` is `selected_sources` and source text was retained. Configure the host's stdio MCP command as your Python executable with these arguments:

```text
<absolute path to career-context-ai>/career_context.py
research-serve
<absolute path to your local context folder>
```

The server exposes admitted snapshots, evidence notes, a pending queue, draft checks and sheet planning. It cannot browse other local files, fetch linked websites or call source services. It exposes selected original text to the connected AI host; the host's provider and data handling still apply. This setting controls this server, not unrelated tools the host may have.

Give the agent the [career-context skill](../skills/career-context-sheet/SKILL.md), the saved work question and access to this server. It can follow the same research-to-sheet protocol as the fictional demo, without another permission loop for already-authorized reads. Preserve private state and avoid copying it to the public checkout. After it saves a checked sheet plan and receives a finishing receipt:

```sh
python career_context.py research-build ../my-career-context ../my-career-context/CAREER-CONTEXT.html --force
```

The demo launcher still accepts only its fixed fictional sources. For larger selected exports, an optional Codex extraction step processes small batches before the host chooses stories:

```sh
python career_context.py research-extract ../my-career-context
python career_context.py research-extract ../my-career-context --max-batches 3
```

The first command reports pending sections locally without calling a model. The second sends at most four admitted sections per call to the authenticated Codex service, for at most three calls. It requires `selected_sources` and retained source text. This is remote model processing even though inputs, outputs and the resulting archive are saved locally. It uses the CLI's default model with tools, memory and user configuration disabled.

The model is asked to retain actions by every contributor, action states and unresolved context; the host checks exact section coverage and citation references. Accepted extractions enter the same research journal consumed by `research-serve`, so the host can recover them through `episode_packet`. Repeat the bounded command to resume pending sections. It never overwrites accepted extractions or automatically retries a failed call. Receipts and the first response remain in `extraction-batches/`; failed or interrupted attempts block further launches for inspection. Codex also uses its normal local runtime state outside the public project; the launcher reuses that directory instead of creating database copies per batch. If the process was forcibly stopped, confirm it has exited before removing a leftover `running.lock`. Do not run the research host concurrently; the server refuses requests while extraction holds that lock. Reconnect an existing host afterwards to load the updated journal.

Policy, capture and journal changes stop the run before another transfer or import. Source permissions are never expanded to follow a reference. The runner reserves journal capacity for later research, but large archives may still need a narrower new workspace. Existing weak extractions are not silently replaced; preserve that attempt and use a new scoped workspace for a fresh comparison.

Extraction is an intermediate step, not a finished biography. Continue with the host to join dates and actors across original sections, distinguish substantive work from chatter, compare reserve episodes, research counterexamples and complete the depth review. More retained events do not prove a better story. The batch checks validate shape, source references and coverage; semantic review and person review remain necessary. There is no automatic whole-archive narrative launcher yet.

## Depth is a checklist, not a collection count

The local checklist distinguishes captured records from records read in research. The [deep research flow](DEEP-RESEARCH-FLOW.md) requires question-led research, a challenge after the first plan and a ten-lens review for each account. It stores findings, counterpoints, remaining questions and attribution coverage alongside the journal. New evidence, notes or a changed plan make the review stale. A completed agent review still leaves person review pending; a high read count does not establish semantic completeness.

This version uses stable snapshots. Identical imports can be repeated before research; conflicting revisions and imports after research begins are refused. The saved run resumes against unchanged captures. For a changed scope or source revision, create a new scoped workspace and retain the previous context as a reference. Automatic synchronization and policy editing with selective deletion are not implemented.
