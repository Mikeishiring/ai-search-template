# Career notebook design contract

The notebook helps a person understand and use the context behind their work. A useful visit ends with a clearer account, an inspected source, a practised story or one consequential detail added. A complete career archive is not a prerequisite.

## The core journey

1. Start with an existing account or one writing prompt.
2. Read a compact account in connected prose.
3. Open its full context and evidence when needed.
4. Answer the most useful unresolved question.
5. See that answer in the account it belongs to, then save or continue.

The agent owns research and initial synthesis within the selected scope. The interface owns reading, orientation, editing and preservation. A local follow-up control does not imply a model call, source search or factual verification.

## Page roles

| Place | The reader's question | Useful next action |
|---|---|---|
| About | Who is this person, and what matters across their work? | Open a concrete account |
| Work & feedback | What happened, what was their part and what supports it? | Inspect context or add the missing detail |
| Quarterly work | What was happening during this explicit period, and how did the approach change? | Follow the linked work account |
| Interview preparation | Which supported story answers this question? | Practise, inspect evidence or resolve a consequential gap |
| Writing | What do I need to add now? | Read the resulting account |
| Review & save | What is retained, and what am I selecting to share? | Download the appropriate file |

Avoid adding a destination unless it has a distinct job. Use the person's work as the main content; template documentation and design comparisons do not belong in their primary navigation.

## Reading and visual hierarchy

Use one stable story frame for short accounts, long accounts, images and feedback. The first image must not trigger an unrelated page layout.

- A specific title and useful period orient the reader.
- Connected prose establishes contribution before a complex artifact needs interpretation.
- Qualifications sit beside the affected outcome. Editorial questions belong in full context or the focused follow-up.
- Actual work images keep their aspect ratio and have a full-size reading path. Captions explain contribution and evidence limits only where necessary.
- Quotes retain the speaker's supported relationship to the work, the setting and the date when available. Do not infer seniority or turn praise into adoption evidence.
- Full context has an explicit destination. The next prompt asks for the missing event or decision, not generic self-promotion.

Use a near-white ground, a white reading surface, neutral type and a small family of grays. Thin rules express alignment and grouping. Stronger contrast marks the title, selected destination and useful action. Whitespace separates ideas; it is not an invitation to add explanatory copy. Color and motion need a semantic purpose. Respect reduced motion.

The reading column must remain comfortable at narrow widths and with long unbroken text. Metadata remains legible. Navigation and image controls retain usable hit targets; mobile gets a deliberate menu rather than a compressed desktop row.

## Navigation and state

The current section and current account are distinct choices. A section changes the reader's task; an account changes the work being examined. Preserve account selection when moving into interview preparation. A quarterly link names its destination and offers a route back to the same quarter.

Use stable routes, browser history and explicit selected states. Opening a source or image preserves the reading position; closing returns focus without stealing a subsequent focus choice. A mobile menu has an accessible name, exposes its state, closes deliberately and keeps destinations reachable by keyboard.

An empty notebook begins with writing. An existing account can be useful before an introduction exists. Empty quarters, missing images and absent quotes do not generate decorative placeholders or fabricated content.

## Evidence and date integrity

The canonical format remains [career-context/v1](../skills/career-context-sheet/references/format.md). Every consequence worth keeping retains its supporting source references, shared credit and uncertainty. A process document is not evidence of independent use; a prototype is not a deployed tool.

Quarterly entries use the explicit [companion contract](../skills/career-context-sheet/references/notebook.md). Work periods, source dates and file revision dates remain distinct. Do not fill a quarter merely to complete a timeline. Cross-quarter work retains its original account period.

## Template and instance relationship

The reusable HTML asset and renderer govern the public demonstration and newly rendered personal notebooks. Instances carry selected context and images; they do not fork the template's visual system by default.

The canonical evidence packet and editable notebook are separate retained layers. Rendering an existing notebook preserves its saved working layer. Reconciliation of edits into canonical evidence is an explicit agent task, not an implied background behavior. Updates must never silently discard the person's corrections or substitute a different notebook's browser state.

Keep all runtime resources inside the standalone HTML. Keep the extracted skill independent of the repository. Bundle only named source files and the license; personal records and incidental build artifacts never become template inputs.

## Acceptance criteria

| Case | Required result |
|---|---|
| One sparse account | A readable first result and one useful next action, without an empty portfolio layout |
| Long account, quote or first image | The same story frame; no clipped evidence, hidden attribution or layout personality switch |
| Explicit quarter | Period, work, pressure and approach remain source-backed; linked account and return route resolve |
| No quarter companion | No invented quarters or date inference |
| Follow-up correction | Saved into the selected account; original records remain separately retained |
| Multiple images | Bytes and hashes survive; all images have a reading path and retain captions |
| HTML reimport | Canonical packet, quarterly companion and saved notebook layer survive independently |
| Source text containing markup | Rendered as inert text in visible content and embedded payloads |
| Offline or JavaScript disabled | Meaningful accounts, evidence, images and explicit quarters remain readable |
| Narrow screen and keyboard | Clear navigation, readable text, usable image/source readers and reliable focus recovery |
| Distribution | Extracted skill renders without repository access; public example is fictional and reproducible |

Run data and packaging checks for each release. Record rendered checks separately: a passing parser test is not a responsive, keyboard or visual acceptance result. Where browser checks cannot be run, state that gap instead of treating the design as verified.
