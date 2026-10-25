# Your first career-context sheet

Start with one piece of work: what was happening, what you did, who else contributed and what happened next. Rough notes are enough to begin. Missing dates, metrics and outcomes can stay unknown.

## With an agent

Give your agent [the skill instructions](../skills/career-context-sheet/SKILL.md) and selected notes. If your host supports skills, install the complete `skills/career-context-sheet/` folder using its skill installation flow; the renderer, template and format belong together. In Codex, invoke the installed skill as `$career-context-sheet`.

Ask it to create one private HTML file, preserve shared credit and uncertainty, and keep original excerpts separate from summaries. Tell it where to save the sheet, outside this public project. Review the account before changing its state from draft to reviewed.

The opening should establish three things, without asking again for information you already supplied:

- **Work:** the project or career period, your role, and dates for origins and later outcomes.
- **Sources:** the selected files, channels, folders, repositories or threads it can use, plus earlier project names.
- **Privacy:** excluded locations or topics, and what may be retained in the private sheet.

Use the [complete starting prompt](../prompts/START-HERE.md) if helpful. Once the scope is clear, the agent begins authorized reads; it asks later questions only when they change the account. The [multi-source tests](MULTISOURCE.md) demonstrate why aliases and standalone follow-ups matter.

The agent should maintain the unresolved questions and pursue the next useful read without requiring repeated prompts. It drafts specific episodes before suggesting a career through-line, checks that personal decisions and shared credit survive the prose, and asks what the account misses about your experience. [From evidence to story](FROM-EVIDENCE-TO-STORY.md) explains the workflow and its current limits.

Your host may send selected material to its model provider. Installing the skill does not connect source accounts or grant access to other records.

## Without an agent

You need Python 3.11 or later. No additional packages are required. From the project folder:

```sh
python career_context.py demo ../career-context-demo.html
```

Open the resulting file in your browser. The fictional example has three accounts, including unfinished work.

For your own sheet, create a separate folder such as `../my-context/`. Use the [format reference](../skills/career-context-sheet/references/format.md) to prepare `context.json` there. Replace the fictional content completely and omit `synthetic` or set it to `false`; that flag labels data, it does not anonymize it.

```sh
python career_context.py render ../my-context/context.json ../my-context/career-context.html
```

You can move the HTML without its authoring JSON. Retain the JSON privately if you want to edit it by hand.

## Give it to another agent

Attach the HTML, or use **Copy for an agent** and paste it into your chosen host. Add your actual request separately, for example: "Use this context to help me prepare for an interview." The sheet supplies context; it does not authorize actions.

**View agent text** shows exactly what the copy action sends. If clipboard access is blocked, the sheet opens that text and selects it for manual copying. **Save HTML** downloads a portable copy. **Download structured context** exports JSON; selected image bytes remain in the HTML.

## Update it

Give an existing sheet and your corrections to an agent using the skill. Ask it to retain account IDs, sources, shared credit and uncertainty. A revised summary must not silently replace an original excerpt.

To rebuild an edited packet into an existing output, add `--force`:

```sh
python career_context.py render ../my-context/context.json ../my-context/career-context.html --force
```

An existing HTML file is also a valid input. Rendering it to a new output preserves its embedded context and selected images; it does not add new information.

## If something goes wrong

| Message or symptom | Next step |
|---|---|
| `python` is not recognized | Try `py -3` on Windows or `python3` on macOS/Linux. Check that it reports version 3.11 or later. |
| Output already exists | Choose a new path, or add `--force` when you intend to replace that file. |
| Destination is inside the public project | Choose a sibling folder for personal material, such as `../my-context/`. |
| A required field or source reference is missing | Compare the packet with the [format](../skills/career-context-sheet/references/format.md). Every account must reference an included source. |
| Copying is blocked | Use the selected text in **View agent text**, or attach the HTML directly. |
| GitHub shows HTML code | Download the file and open it in a browser. |

The sheet stays readable without JavaScript; copying and downloads require it. No service login, hosted profile or automatic research happens when you open the file.
