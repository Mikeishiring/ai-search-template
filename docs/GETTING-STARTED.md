# Your first career-context sheet

Start with one piece of work: what was happening, what you did, who else contributed and what happened next. Rough notes are enough. Missing dates, metrics and outcomes can stay unknown.

## Use the complete skill

The `skills/career-context-sheet/` folder contains the instructions, research references, renderer and HTML template. Keep those files together.

From the downloaded project, create the standalone bundle:

```sh
python tools/build_skill.py ../career-context-sheet.zip
```

You need Python 3.11 or later. No packages are required. On macOS/Linux, use `python3` if needed; on Windows, `py -3` may be available.

| Host | Setup |
|---|---|
| Codex | Place the extracted `career-context-sheet` folder under `~/.agents/skills/` or a project's `.agents/skills/`, then invoke `$career-context-sheet`. [Official setup](https://learn.chatgpt.com/docs/build-skills). |
| Claude | Upload the ZIP through **Customize > Skills**. Code execution and file creation must be enabled. [Official setup](https://support.claude.com/en/articles/12512180-use-skills-in-claude). |
| Another agent | Give it the extracted folder and ask it to follow `SKILL.md`. It needs file access and Python to render the supplied template. A text-only model can help prepare the account, but cannot run the renderer. |

Host support is separate from output quality. The tests check the extracted renderer and portable file; they do not establish equivalent research quality across models.

## Make your first account

Give the agent selected notes and ask:

> Use the career-context-sheet skill to make one private HTML file from this material. Preserve my decisions, shared credit and uncertainty. Reuse what I have already told you; ask only about missing scope or facts that change the account.

The opening establishes the work, permitted source locations and privacy boundaries once. Keep inputs, working notes and outputs outside the public checkout. The agent investigates consequential questions, drafts specific episodes, challenges the account and asks what the records miss about your experience.

The [longer starting prompt](../prompts/START-HERE.md) is available for broader research. Existing material and corrections should carry forward, including your wording when it is selected as an exact account. Review the result before changing its state from draft to reviewed.

## Read, reuse and update

Open the HTML in a browser. **Preview text** shows exactly what **Copy for an agent** copies. If clipboard access fails, the text is selected for manual copying. **Save full HTML** downloads the portable file; **Download full JSON** exports JSON while selected image bytes remain in the HTML.

Attach the HTML to another agent with a separate request, such as: "Use this context to help me prepare for an interview." The file includes selected source excerpts as well as the visible account; review it before sharing.

To update it, give the existing HTML and corrections to the skill. Keep account IDs, original excerpts, shared credit and uncertainty. Re-rendering an existing file preserves its embedded context and images.

## Prepare for an interview

Ask the agent to [prepare an interview](../skills/career-context-sheet/references/interview-prep.md) from your career context and any target you have supplied. It gathers authorized context, selects the strongest stories and drafts all six parts, including an introduction, answers, chapters and timelines. Review the result and practise; answer only the important gaps the available material cannot resolve.

**Copy for your coach** carries the prepared draft and its evidence into your model. Correct the career-context source and ask the agent to regenerate the preparation when facts change. Copy the HTML file itself to move it between devices.

## Render without an agent

From the full project:

```sh
python career_context.py demo ../career-context-demo.html
python career_context.py render ../my-context/context.json ../my-context/career-context.html
```

Prepare personal JSON using [the format](../skills/career-context-sheet/references/format.md). Replace fictional content completely; omit `synthetic` or set it to `false`. That label does not anonymize data.

From a standalone skill, run its renderer directly:

```sh
python scripts/render_context.py ../my-context/context.json ../my-context/career-context.html
```

Resolve that script from the extracted skill folder. Existing HTML is also valid input. Both entrypoints preserve an existing output unless you add `--force`; malformed input leaves the old file intact.

## Keep a local database

The agent can create the database and HTML together from the context it has prepared:

```sh
python skills/career-context-sheet/scripts/archive_context.py build ../my-input/context.json ../my-context
python skills/career-context-sheet/scripts/archive_context.py search ../my-context/career.sqlite "project"
```

Open `../my-context/CAREER-CONTEXT.html`. Keep `career.sqlite` private; it contains selected sources, images and historical revisions. Use `build --update` to retain corrections in the same database. The [archive guide](../skills/career-context-sheet/references/local-archive.md) explains recovery and retention.

## Create a resume

Give the agent your context plus any target and reference resume. Ask it to follow the [resume guide](../skills/career-context-sheet/references/resume.md) and produce the populated draft. It adapts section order and wording to your experience, preserves evidence links, and does not invent missing titles or dates. The HTML includes a private evidence review, print/PDF layout and plain-text download. Review the printed/text version before using it; those exports omit the underlying evidence.

## Larger source collections

The full repository also provides [local context setup](LOCAL-CONTEXT.md) and an optional research MCP server for selected exports. It adds saved source boundaries, research state and a depth review. These components are not needed to create or read a sheet and are not included in the standalone bundle.

[Privacy and storage](PRIVACY.md) explains what is retained and what your chosen model receives.

Copy all accounts or select one; private source excerpts are excluded from copied text unless selected. Attribution and limits remain. Full HTML and JSON always include all selected sources. Optional links lead to separately delivered local files.
