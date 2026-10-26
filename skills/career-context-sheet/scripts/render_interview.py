"""Render model-prepared interviews from a current, portable career-context file."""
import argparse
import copy
from datetime import date
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import tempfile

_spec = importlib.util.spec_from_file_location("career_context_renderer", Path(__file__).with_name("render_context.py"))
render_context = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(render_context)

SCHEMA = "interview-preparation/v1"
WORKFLOW = [
    "Gather relevant context from sources the person has already authorized. Reuse existing accounts before asking for information.",
    "Choose the strongest supported evidence and core stories for the stated target; do not invent a target.",
    "Draft an introduction with supportable follow-up points in the person's voice.",
    "Decode likely questions, select a relevant story and draft a direct answer.",
    "Give longer stories clear chapters, preserving decisions, shared credit, corrections and outcomes.",
    "Show the recorded sequence and feedback cycles without inventing dates or speed. Ask only consequential unresolved questions.",
]
NAV = [
    ("signal", "Focus"), ("stories", "Stories"),
    ("opening", "Introduction"), ("decode", "Answers"),
    ("chapters", "Chapters"), ("pace", "Pace"),
]
ID = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}")
TOKEN = re.compile(r"__([A-Z_]+)__")


def shape(value, required, label, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError(f"{label} needs exactly these fields: {', '.join(required)}" +
                         (f"; optional: {', '.join(optional)}" if optional else ""))


def text(value, label):
    render_context.check_text(value, label, maximum=15000)
    if not value.strip():
        raise ValueError(f"{label} must not be blank")


def collection(value, label, minimum=1, maximum=80):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} needs {minimum} to {maximum} entries")


def fingerprint(source):
    return hashlib.sha256(source.read_bytes()).hexdigest()


def inspect_context(source):
    raw = source.read_bytes()
    packet = render_context.parse_packet(raw.decode("utf-8"), is_html=source.suffix.lower() in {".html", ".htm"})
    render_context.validate(packet)
    return {"contextSha256": hashlib.sha256(raw).hexdigest(), "context": packet}


def prepare(context, projection, context_sha256):
    render_context.validate(context)
    shape(projection, ["schema", "contextSha256", "preparedOn", "target", "headline", "throughline",
                       "signals", "stories", "opening", "questions", "priorityGap"], "Preparation")
    if projection["schema"] != SCHEMA:
        raise ValueError("Unsupported preparation schema")
    if projection["contextSha256"] != context_sha256:
        raise ValueError("Career context changed. Read the current file and regenerate the preparation.")
    date.fromisoformat(projection["preparedOn"])
    if projection["target"] is not None:
        text(projection["target"], "Target")
    for key in ("headline", "throughline"):
        text(projection[key], key)
    collection(projection["opening"], "Opening", maximum=4)
    for paragraph in projection["opening"]:
        text(paragraph, "Opening paragraph")
    collection(projection["stories"], "Stories")
    accounts = {a["id"]: a for a in context["accounts"]}
    sources = {s["id"]: s for s in context["sources"]}
    stories, ids = [], set()
    for draft in projection["stories"]:
        shape(draft, ["id", "tests", "takeaway", "chapters", "timeline"], "Story")
        key = draft["id"]
        if not isinstance(key, str) or key not in accounts or key in ids:
            raise ValueError("Stories must reference unique account IDs from the current context")
        ids.add(key)
        for field in ("tests", "takeaway"):
            text(draft[field], field)
        for field, keys in (("chapters", ["title", "text"]), ("timeline", ["when", "text"])):
            collection(draft[field], field, maximum=12)
            for entry in draft[field]:
                shape(entry, keys, field)
                for name in keys:
                    text(entry[name], field + "/" + name)
        account = copy.deepcopy(accounts[key])
        # The original file retains images. Carry all narrative fields and source text;
        # never pull local artifact files into a derived preparation.
        account.pop("artifacts", None)
        stories.append({**copy.deepcopy(draft), "title": account["title"], "when": account["period"],
                        "account": account, "evidence": [copy.deepcopy(sources[ref]) for ref in account["sourceRefs"]]})
    collection(projection["signals"], "Signals", maximum=3)
    lead_ids = []
    for signal in projection["signals"]:
        shape(signal, ["title", "reason", "storyId"], "Signal", optional=["summary"])
        if signal["storyId"] not in ids or signal["storyId"] in lead_ids:
            raise ValueError("Signals must reference distinct selected stories")
        lead_ids.append(signal["storyId"])
        for field in ("title", "reason", *(["summary"] if "summary" in signal else [])):
            text(signal[field], field)
    collection(projection["questions"], "Questions", maximum=12)
    question_ids = set()
    for question in projection["questions"]:
        shape(question, ["id", "question", "tests", "storyId", "reason", "answer"], "Question", optional=["label"])
        key = question["id"]
        if not isinstance(key, str) or not ID.fullmatch(key) or key in question_ids:
            raise ValueError("Questions need unique safe IDs")
        question_ids.add(key)
        if question["storyId"] not in ids:
            raise ValueError("Question references an unselected story")
        for field in ("question", "tests", "reason", "answer", *(["label"] if "label" in question else [])):
            text(question[field], field)
    gap = projection["priorityGap"]
    if gap is not None:
        shape(gap, ["storyId", "question", "why"], "Priority gap", optional=["label"])
        if gap["storyId"] not in ids:
            raise ValueError("Priority gap references an unselected story")
        for field in ("question", "why", *(["label"] if "label" in gap else [])):
            text(gap[field], field)
    return {**copy.deepcopy(projection), "stories": stories, "leadStoryIds": lead_ids,
            "synthetic": context.get("synthetic", False), "reviewStatus": "draft",
            "person": copy.deepcopy(context["person"]),
            "contextReviewStatus": context["reviewStatus"], "contextUpdatedAt": context["updatedAt"],
            "availableAccountCount": len(accounts), "modelWorkflow": WORKFLOW}


def escaped(value):
    return html.escape(str(value), quote=True)


def paragraphs(value):
    return "".join(f"<p>{escaped(part)}</p>" for part in value.split("\n\n") if part.strip())


def bullets(values):
    return "<ul>" + "".join(f"<li>{escaped(value)}</li>" for value in values) + "</ul>" if values else ""


def source_details(story):
    account = story["account"]
    original = "".join(f"<h4>{label}</h4>{paragraphs(account[key])}" for key, label in (
        ("summary", "Original summary"), ("context", "Context"), ("aim", "Aim"),
        ("contribution", "Personal contribution"), ("sharedCredit", "Shared work"), ("outcome", "Outcome")))
    original += "<h4>Evidence limits</h4>" + bullets(account["limits"])
    original += "<h4>Decisions</h4>" + bullets(account["decisions"])
    if account["questions"]:
        original += "<h4>Still to clarify</h4>" + bullets(account["questions"])
    evidence = []
    for source in story["evidence"]:
        metadata = " · ".join(part for part in [source["kind"].replace("_", " "), source.get("date")] if part)
        locator = f'<p class="meta">{escaped(source["locator"])}</p>' if source.get("locator") else ""
        evidence.append(f'<article class="source"><h3>{escaped(source["label"])}</h3>'
                        f'<p class="meta">{escaped(metadata)}</p>{paragraphs(source["content"])}'
                        f'<p class="meta">{escaped(source["scope"])}</p>{locator}</article>')
    return (f'<details class="reference original-account"><summary>Original account and sources</summary>{original}'
            f'<div id="evidence-{escaped(story["id"])}">{"".join(evidence)}</div></details>')


def render_html(packet):
    by_id = {s["id"]: s for s in packet["stories"]}
    stories = [by_id[key] for key in packet["leadStoryIds"]] + [s for s in packet["stories"] if s["id"] not in packet["leadStoryIds"]]
    def story_options(group):
        return "".join(f'<option value="{escaped(s["id"])}">{escaped(s["title"])}</option>' for s in group)
    lead_count = len(packet["leadStoryIds"])
    options = '<optgroup label="Lead stories">' + story_options(stories[:lead_count]) + '</optgroup>'
    if len(stories) > lead_count:
        options += '<optgroup label="For specific questions">' + story_options(stories[lead_count:]) + '</optgroup>'
    signals = "".join(
        f'<li><h3><a href="#stories/{escaped(s["storyId"])}">{escaped(s["title"])}'
        f'<span class="arrow" aria-hidden="true">→</span></a></h3><p>{escaped(s.get("summary", s["reason"]))}</p></li>'
        for s in packet["signals"])
    selection_notes = ('<details class="reference selection-notes"><summary>Why these stories</summary>' +
        paragraphs(packet["throughline"]) + "".join(
            f'<section><h3>{escaped(s["title"])}</h3><p>{escaped(s["reason"])}</p>' +
            bullets(by_id[s["storyId"]]["account"]["limits"]) +
            f'<button class="quiet" data-sources="{escaped(s["storyId"])}">Sources</button></section>'
            for s in packet["signals"]) + '</details>')
    gap = packet["priorityGap"]
    gap_html = (f'<details class="reference gap"><summary>{escaped(gap.get("label", "One open question"))}</summary>'
                f'<h3>{escaped(gap["question"])}</h3><p>{escaped(gap["why"])}</p>'
                '<button class="quiet" data-copy="gap">Copy question</button></details>') if gap else ""
    story_html, chapter_html, pace_html = [], [], []
    for index, story in enumerate(stories):
        account, key = story["account"], escaped(story["id"])
        attr = f'data-story-panel="{key}" class="reading' + (" is-selected" if index == 0 else "") + '"'
        heading = (f'<header class="story-heading"><h2>{escaped(story["title"])}</h2>'
                   f'<p class="meta">{escaped(story["when"])}</p></header>')
        action = f'<button class="quiet" data-sources="{key}">Sources and scope</button>'
        limits = ('<details class="reference evidence-limits"><summary>Evidence limits</summary>' +
                  bullets(account["limits"]) + '</details>') if account["limits"] else ""
        story_html.append(
            f'<article {attr}>{heading}<p class="takeaway">{escaped(story["takeaway"])}</p>'
            f'<h3>What happened</h3>{paragraphs(account["outcome"])}<h3>Your part</h3>{paragraphs(account["contribution"])}'
            f'<h3>Shared work</h3>{paragraphs(account["sharedCredit"])}'
            f'<div class="story-actions"><a class="quiet" href="#chapters/{key}">Read the chapters '
            f'<span class="arrow" aria-hidden="true">→</span></a>{action}</div>'
            f'<details class="reference"><summary>Why this story fits</summary><p>{escaped(story["tests"])}</p>'
            f'{bullets(account["limits"])}</details>{source_details(story)}</article>')
        chapters = "".join(f'<li><div><h4>{escaped(c["title"])}</h4>{paragraphs(c["text"])}</div></li>' for c in story["chapters"])
        chapter_html.append(f'<article {attr}>{heading}<p class="takeaway">{escaped(story["takeaway"])}</p>'
                            f'<ol class="chapters">{chapters}</ol><div class="story-actions">{action}'
                            f'<a class="quiet" href="#pace/{key}">See the timeline <span class="arrow" aria-hidden="true">→</span></a></div>{limits}</article>')
        milestones = "".join(f'<li><strong>{escaped(m["when"])}</strong> — {escaped(m["text"])}</li>' for m in story["timeline"])
        pace_html.append(f'<article {attr}>{heading}<ol class="pace">{milestones}</ol>{action}{limits}</article>')
    questions = []
    for index, question in enumerate(packet["questions"]):
        key = escaped(question["storyId"])
        notes = (f'<details class="reference answer-notes"><summary>Reasoning and evidence limits</summary>'
                 f'<h4>What it may test</h4><p>{escaped(question["tests"])}</p>'
                 f'<h4>Why this story</h4><p>{escaped(question["reason"])}</p>'
                 f'<a class="quiet" href="#stories/{key}">{escaped(by_id[question["storyId"]]["title"])}</a>' +
                 bullets(by_id[question["storyId"]]["account"]["limits"]) + '</details>')
        questions.append(
            f'<article data-question-panel="{escaped(question["id"])}" class="question' + (" is-selected" if index == 0 else "") +
            f'"><h2 class="question-title">{escaped(question["question"])}</h2><div class="answer">{paragraphs(question["answer"])}</div>'
            f'<div class="answer-actions"><button class="quiet" data-copy="answer" data-question-id="{escaped(question["id"])}">Copy answer</button>'
            f'<button class="quiet" data-sources="{key}">Sources</button><span class="copy-feedback" role="status"></span></div>{notes}</article>')
    values = {
        "TARGET_NOTE": escaped(packet["target"] or "Prepared from your context · no target role selected"),
        "HEADLINE": escaped(packet["headline"]), "THROUGHLINE": escaped(packet["throughline"]),
        "DEMO": '<p class="demo-notice" id="synthetic-note">Fictional example · these work accounts are invented.</p>' if packet["synthetic"] else "",
        "NAV": "".join(f'<a href="#{key}"' + (' aria-current="page"' if i == 1 else "") + f'>{label}</a>' for i, (key, label) in enumerate(NAV, 1)),
        "OPTIONS": "".join(f'<option value="{key}">{label}</option>' for i, (key, label) in enumerate(NAV, 1)),
        "SIGNALS": signals, "SELECTION_NOTES": selection_notes, "GAP": gap_html, "STORY_OPTIONS": options, "STORIES": "".join(story_html),
        "OPENING": "".join(paragraphs(p) for p in packet["opening"]),
        "PROFILE": '<details class="reference"><summary>Original profile context</summary>' +
                   paragraphs(packet["person"]["overview"]) + bullets(packet["person"].get("background", [])) + "</details>",
        "FLAGS": "".join(f'<a href="#stories/{escaped(s["storyId"])}">{escaped(by_id[s["storyId"]]["title"])} <span class="arrow" aria-hidden="true">→</span></a>' for s in packet["signals"]),
        "QUESTION_OPTIONS": "".join(f'<option value="{escaped(q["id"])}">{escaped(q.get("label", q["question"]))}</option>' for q in packet["questions"]),
        "QUESTIONS": "".join(questions), "CHAPTERS": "".join(chapter_html), "PACE": "".join(pace_html),
        "PREPARED_ON": escaped(packet["preparedOn"]),
        "SCOPE": f'Model draft · {len(packet["stories"])} selected accounts from {packet["availableAccountCount"]}. Context dated {escaped(packet["contextUpdatedAt"])}; ' + ("reviewed by the person." if packet["contextReviewStatus"] == "person_reviewed" else "draft for review."),
        "DATA": json.dumps(packet, ensure_ascii=True).replace("<", "\\u003c").replace("&", "\\u0026"),
    }
    template = (render_context.SKILL / "assets/interview.html").read_text(encoding="utf-8")
    # One substitution pass keeps placeholder-like source text literal.
    return TOKEN.sub(lambda match: values[match[1]], template)


def render(source, projection_source, destination, *, overwrite=False):
    inspected = inspect_context(source)
    if projection_source.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Preparation projection exceeds 4 MiB")
    projection = json.loads(projection_source.read_text(encoding="utf-8"))
    packet = prepare(inspected["context"], projection, inspected["contextSha256"])
    output = render_html(packet).encode("utf-8")
    if destination.is_symlink():
        raise ValueError("Output must not be a symbolic link.")
    if destination.resolve() in (source.resolve(), projection_source.resolve()):
        raise ValueError("Use a separate output so the source files are preserved.")
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".career-interview-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(output)
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": str(destination), "accounts": len(packet["stories"]),
            "bytes": len(output), "sha256": hashlib.sha256(output).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Current career-context JSON or HTML")
    parser.add_argument("projection", nargs="?", type=Path, help="Model-authored preparation JSON")
    parser.add_argument("output", nargs="?", type=Path, help="Private interview HTML destination")
    parser.add_argument("--inspect", action="store_true", help="Read context with its fingerprint for drafting")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args(argv)
    try:
        source = args.input.expanduser().resolve()
        if args.inspect:
            if args.projection or args.output or args.force:
                raise ValueError("--inspect accepts only the context input.")
            result = inspect_context(source)
        else:
            if not args.projection or not args.output:
                raise ValueError("Supply the model's preparation JSON and an HTML destination.")
            projection = args.projection.expanduser().resolve()
            destination = args.output.expanduser().absolute()
            if destination.suffix.lower() not in {".html", ".htm"}:
                raise ValueError("Choose an output ending in .html or .htm.")
            if destination.resolve().is_relative_to(render_context.SKILL.resolve()):
                raise ValueError("Keep personal outputs outside the installed skill folder.")
            if not destination.parent.is_dir():
                raise ValueError("Create the output folder first.")
            if destination.exists() and not args.force:
                raise ValueError("Output already exists; use --force to replace it.")
            result = render(source, projection, destination, overwrite=args.force)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Could not create interview preparation: {error}\n")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
