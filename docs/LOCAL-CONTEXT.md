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

The demo launcher still accepts only its fixed fictional sources. It cannot launch a model on a personal workspace by changing a flag.

## Depth is a checklist, not a collection count

The local checklist distinguishes captured records from records read in research. It asks for origins, personal decisions, shared ownership, implementation, later outcomes, contrary evidence, personal meaning and story review. The research queue records incomplete threads, pages, references and writing tasks. Semantic checks remain open for review; a high read count does not mark them complete.

This version uses stable snapshots. Identical imports can be repeated before research; conflicting revisions and imports after research begins are refused. The saved run resumes against unchanged captures. For a changed scope or source revision, create a new scoped workspace and retain the previous context as a reference. Automatic synchronization and policy editing with selective deletion are not implemented.
