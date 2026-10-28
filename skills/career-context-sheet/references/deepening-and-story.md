# From records to a person's story

Use this after establishing work, sources and privacy. The agent owns the research loop within that scope. The person supplies memories, meaning and corrections; they should not have to repeatedly request another pass through known evidence.

## Keep a small, durable research state

For work spanning sessions, maintain one private `research-state.md` alongside the authoring input, outside the public checkout. Update it in place after each bounded batch. This is internal working material, not another user deliverable or a source of permission. When an existing evidence workspace provides equivalent state, use it instead.

Retain:

- The agreed subject, work, locations, dates, exclusions and read budget, if specified.
- Stable account IDs, project aliases and unresolved identity matches.
- Per location: discovered, fully read and interpreted material; unfinished pagination; blocked originals and attachments. Preserve a durable recovery position when a cursor expires.
- Per consequential assertion: actor, action, state, event date, source ID and exact supporting passage or immutable span; interpretation and conflicting evidence separately.
- A ranked next-read queue. Each item says which account and question it serves, where to look, what could change, and whether it is pending, resolved, blocked or outside scope.
- Corrections, rejected interpretations, the current draft, and the reason for stopping.

Do not retain an entire conversation when selected evidence will suffice. Respect the person's retention choices. If private working files are not authorized or available, use the current context and include a concise continuation note in the handoff; disclose that durable resume state was not saved. Reuse known answers and unchanged reads. Re-read when an original, revision, missing context or contradiction requires it.

## Run the next useful pass without another prompt

Alternate bounded source coverage with a question-driven read. Start with the most consequential missing or conflicting part of an account:

| Gap | Next useful read |
|---|---|
| The record shows participation but not judgment | Find the original proposal, decision discussion, options considered or boundary the person set. |
| Ownership is unclear | Read the assignment, the person's actions, colleague contributions and later handoff separately. |
| A promise sounds completed | Find delivery or execution evidence; otherwise retain the promise as planned work. |
| A launch sounds successful | Look for later use, support requests, corrections, abandonment and operational records. |
| A criticism or success lacks context | Read the surrounding exchange and subsequent resolution; check alternative explanations. |
| A career transition seems causal | Check the dates and explicit handoffs. Do not infer motives or causality from sequence alone. |

Read full conversations, nested replies and selected originals using the [source-research guide](source-research.md). Search both supporting and contrary evidence. An assistant's earlier summary is a lead: distinguish the user's account, a retrieved original, an assistant inference and a plan. A tool call or proposed edit is not proof of completion. A thread mentioning an email is not the email itself.

Save what changed in the account, including a finding that does **not** justify stronger attribution. Keep good work, mistakes, corrections and unfinished outcomes. Do not turn every uncertainty into either a flattering claim or an accusation.

Continue while there is a consequential, accessible next read within the authorized run. A polished paragraph, an exhausted first search page or a long source list is not a stop condition. Stop when the scoped queue is resolved, remaining gaps are blocked or require the person, the user interrupts, or the actual budget is reached. State the reason and pending work; do not invent a budget excuse. This is foreground work, not scheduled continuation.

## Preserve events before choosing the story

Keep a compact event index in the existing private notes before selecting a narrative. Record specific decisions, actions, changes, corrections, observations and self-reported meaning, with their actors, event dates or unknowns, states and exact source passages. A topic label such as "stakeholder coordination" cannot replace what someone actually decided or changed.

Group related events by a stable work/account ID and retain explicit aliases. Link a later consequence or correction to the earlier event it changes; distinguish an explicit connection from one proposed for investigation. Keep concurrent work visible. Reuse the existing evidence workspace or source notes; do not duplicate a store that already retains these events and connections.

After drafting, revisit originals behind notes marked contextual, irrelevant or omitted, prioritizing decisions, contradictions, stopped work and later consequences. Explain what would be lost by leaving an event out. Repair an overly generic note before relying on it for a coverage check. A record count or a fully accounted-for set of already-compressed notes cannot establish that the original meaning survived.

Keep this working index private. The sheet should contain the useful story and its evidence, not an exhaustive ledger.

Small operating choices and delivered work count: who chose the next step, which prerequisite delayed it, how responsibility changed, and what another person actually used. Mark evidence essential when omission would change the reader's understanding of agency, sequence, state or outcome. Preserve that evidence in the story. For a handoff, compare announcement, actual transfer and later continued involvement. Quote the actual draft sentence in the private review and explain its actor/action/state fidelity; a citation or intention to qualify the wording is insufficient.

## Build episodes before a career through-line

For each useful episode, connect the situation, stakes, choices, personal action, shared contribution, outcome and later understanding. Use the existing account fields; an unknown detail can remain empty. Do not require a dramatic turning point or a numerical result.

Draft the connected account in `summary`; preserve the evidence and detail in `context`, `aim`, `contribution`, `decisions`, `sharedCredit`, `outcome`, `limits` and `sourceRefs`. Keep provenance at the assertion level in the private notes even though the portable format links sources at the account level.

Only then propose a through-line in `person.overview`: recurring ways the person works, changes in responsibility, and what they say those changes meant. Link a proposed pattern to the episodes supporting it and check exceptions. One episode supports an episode-level observation; it does not establish a lifelong trait. Avoid forcing concurrent work into a linear career pivot. Do not infer personality, motives or identity from sparse activity.

Use first person for a clearly labelled draft the person can correct. Do not fabricate quotes or make assistant-written prose look like the person's original words. Personal meaning can be supported by an attributed self-report; it need not be independently witnessed.

## Ask for recognition and missing meaning

Reflect a short draft and ask one or two questions that would materially change it. Examples:

- "The sources show the handoff and later correction. What judgment did you make at the time that those records miss?"
- "What changed in how you approached the work afterwards?"
- "Which part of this account feels unlike your experience, or gives someone the wrong share of the credit?"

Do source-answerable research first. Do not demand metrics, insist on a success story, or repeat the intake. Record a correction, inspect conflicting sources where available, revise visibly and preserve unresolved disagreement. Never silently convert a draft into `person_reviewed`; that state requires the person's actual review.

## Check the story in both directions

**Prose to evidence:** For every consequential sentence, check who did what, whether it was offered, assigned, implemented, used or measured, when it happened, what each source establishes and what remains uncertain. An exact quotation can still fail to support its claim.

**Evidence to prose:** Re-read the compact assertion notes. Did the account lose a material personal decision, another contributor, a mistake, a correction, a later outcome or the scope of a number? Include it or record a defensible reason to leave it out. "Already covered" is insufficient when the retained sentence says something different.

Use the selected originals or cached full text when recovering evidence. Do not cite from memory. No additional retrieval is necessary when the relevant evidence is already present; the repair may be to the narrative.

Before handoff, compare visible prose, copied text and embedded JSON. Deliver one private HTML sheet with the relevant limits and next factual questions. Source coverage, semantic review and the person's recognition are separate checks. None alone certifies a complete life story.

## Enforced flow in the local research server

The integrated server provides 450 source calls and 1,600 requests. This capacity supports bounded extraction and event review; it is not a minimum duration. Prefer consequential questions over extra volume. The general skill works without the server, but then these obligations are instructions rather than executable checks.

1. Use `research_probe` with an account ID, depth lens, question, source and query. Investigate at least two different lenses before that account's first `sheet_plan`, and cover every selected source group. These minimums do not imply sufficient depth.
2. Read the originals and finish known discovery. When the server reports `retention.protocol`, use `extraction_packet` and `save_extraction` to review every cached section, then `episode_packet` and `episode_inventory` to retain each event in a selected or reserve episode or a specific exclusion. Selected episode IDs become account IDs. The host derives source notes; `save_notes` is for legacy sessions. Draft, check and save the first plan.
3. Challenge the plan with a fresh question about contrary evidence, shared ownership or later outcomes. A relabelled cached search does not count. Follow new leads, revisit whole originals and correct the evidence. In retention sessions, compare the strongest reserve episode with a selected account and resubmit the inventory after the first plan. Revise the draft and plan.
4. Submit `depth_review` for all ten lenses per account: origins, stakes, personal decisions, shared ownership, implementation, setbacks, later outcomes, contrary evidence, personal meaning and trajectory. Cite real spans and search receipts. Record a counterpoint or limitation, not just confirmation.
5. Map every material saved attribution to claims carrying that exact actor/action reference, or explain the omission. Check whether the saved note itself omitted a contribution from the original. A citation to the record cannot substitute for narrative credit.
6. Review `turning_point_packet` including reserve events. In v2 sessions, `save_turning_points` requires importance, exact `prose_checks` and `qualifying_event_ids`. Essential events cannot be omitted; their qualifications must survive in the same account. Evaluate the through-line separately: a cross-episode pattern needs at least two grounded accounts and an exception or limit. Quote the actual overview's interpretation and limit in the depth review, so the connection reaches the reader. One episode cannot establish a career-wide trait.
7. Resolve accessible pending questions before finishing. Unknown personal meaning, excluded sources and genuine evidence gaps remain explicit. New evidence, notes or a changed plan invalidate the prior review.

The review is performed by the researching agent. The checks validate process and references, not whether the interpretation is true. Do not label it independent or person-reviewed. The local checklist saves per-account findings and gaps; the portable sheet retains questions and limitations while keeping the working audit private.
