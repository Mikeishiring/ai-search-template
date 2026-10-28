"""Render an editable notebook while preserving its canonical career context."""
import argparse
import base64
import copy
from datetime import datetime, timezone
import hashlib
import html
from html.parser import HTMLParser
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

_spec = importlib.util.spec_from_file_location("notebook_context_renderer", Path(__file__).with_name("render_context.py"))
context_renderer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(context_renderer)
SKILL = Path(__file__).resolve().parents[1]
QUARTER_FIELDS = {"id", "period", "title", "focus", "actions", "tension", "style", "questions", "sourceRefs", "accountId"}
ACCOUNT_TEXT = ("id", "title", "period", "artifact", "problem", "responsibility", "choice", "alternative", "cost", "reason", "action", "after", "shared", "limit", "context", "openQuestions", "scopeTopic", "privateNotes", "publicLink")


class PayloadReader(HTMLParser):
    """Read JSON data only; never execute an imported document."""
    def __init__(self):
        super().__init__()
        self.active = None
        self.parts = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        selected = attrs.get("id")
        if tag == "script" and selected in {"career-draft-data", "career-quarters-data"}:
            if selected in self.parts:
                raise ValueError(f"Duplicate {selected} payload")
            self.active = selected
            self.parts[selected] = []

    def handle_data(self, data):
        if self.active:
            self.parts[self.active].append(data)

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = None

    def value(self, name):
        return json.loads("".join(self.parts[name])) if name in self.parts else None


def imported_payloads(source):
    reader = PayloadReader()
    if source.suffix.lower() in {".html", ".htm"}:
        reader.feed(source.read_text(encoding="utf-8"))
    return reader


def validate_quarters(companion, packet):
    context_renderer.keys(companion, ["schema", "quarters", "synthetic"], "Quarter companion")
    if companion.get("schema") != "career-quarters/v1" or not isinstance(companion.get("quarters"), list):
        raise ValueError("Quarter companion needs schema career-quarters/v1 and a quarters list")
    if "synthetic" in companion and (not isinstance(companion["synthetic"], bool) or companion["synthetic"] != bool(packet.get("synthetic"))):
        raise ValueError("Quarter companion synthetic status must match the context")
    if len(companion["quarters"]) > 160:
        raise ValueError("At most 160 explicit quarters are supported")
    accounts = {a["id"] for a in packet["accounts"]}
    sources = {s["id"] for s in packet["sources"]}
    seen = set()
    for quarter in companion["quarters"]:
        if not isinstance(quarter, dict) or set(quarter) != QUARTER_FIELDS:
            raise ValueError("Each quarter needs exactly the documented quarter fields")
        for key in QUARTER_FIELDS - {"actions", "questions", "sourceRefs"}:
            context_renderer.check_text(quarter[key], f"Quarter {key}")
        qid = quarter["id"]
        if not re.fullmatch(r"[0-9]{4}-Q[1-4]", qid) or qid in seen:
            raise ValueError("Quarter IDs must be unique YYYY-Q1 through YYYY-Q4 values")
        seen.add(qid)
        if quarter["period"] != qid.replace("-", " "):
            raise ValueError("Quarter period must match its ID, for example 2030 Q1")
        if quarter["accountId"] not in accounts:
            raise ValueError("Quarter accountId must resolve to an included account")
        for key in ("actions", "questions", "sourceRefs"):
            if not isinstance(quarter[key], list):
                raise ValueError(f"Quarter {key} must be a list")
            for value in quarter[key]:
                context_renderer.check_text(value, f"Quarter {key} item")
        refs = quarter["sourceRefs"]
        if not refs or len(set(refs)) != len(refs) or set(refs) - sources:
            raise ValueError("Quarter sourceRefs must resolve uniquely to included sources")
    return companion


def source_view(source):
    locator = source.get("locator", "")
    try:
        url = locator if urlsplit(locator).scheme in {"https", "http"} and urlsplit(locator).netloc else ""
    except ValueError:
        url = ""
    text = source["content"] + ("\n\nScope: " + source["scope"] if source["scope"] else "")
    if locator:
        text += "\n\nLocator: " + locator
    return {"title": source["label"], "date": source.get("date", ""), "url": url,
            "text": text, "originalKind": source["kind"],
            "kind": "recollection" if source["kind"] == "person_account" else "record"}


def prepared_packet(source):
    packet = context_renderer.load_packet(source)
    context_renderer.validate(packet)
    packet = copy.deepcopy(packet)
    images = {}
    for account in packet["accounts"]:
        for artifact in account.get("artifacts", []):
            mime, raw = context_renderer.image_data(artifact, source.parent)
            images[artifact["id"]] = f"data:{mime};base64," + base64.b64encode(raw).decode()
            artifact.pop("file", None)
            artifact.pop("_dataUrl", None)
            artifact.update(embeddedId="artifact-" + artifact["id"], mediaType=mime, sha256=hashlib.sha256(raw).hexdigest())
    return packet, images


def context_sections(account):
    sections = [("Summary", account["summary"]), ("Context", account["context"]), ("Aim", account["aim"]),
                ("Personal contribution", account["contribution"]), ("Decisions and approach", account["decisions"]),
                ("Shared work", account["sharedCredit"]), ("Outcome", account["outcome"]),
                ("Limits", account["limits"]), ("Open factual questions", account["questions"])]
    return [(label, "\n".join(value) if isinstance(value, list) else value) for label, value in sections]


def draft_from_packet(packet, images, companion):
    fingerprint = hashlib.sha256(json.dumps(packet, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    source_map = {s["id"]: source_view(s) for s in packet["sources"]}
    accounts = []
    def image_view(artifact):
        return {"data": images[artifact["id"]], "alt": artifact["title"],
                "caption": artifact["caption"], "date": "", "share": False}
    for account in packet["accounts"]:
        artifacts = account.get("artifacts", [])
        first = artifacts[0] if artifacts else None
        complete = "\n\n".join(label + "\n" + text for label, text in context_sections(account) if text)
        for artifact in artifacts:
            complete += "\n\nArtifact: " + artifact["title"] + "\n" + artifact["caption"]
        accounts.append({"id": account["id"], "title": account["title"], "period": account["period"],
                         "artifact": first["title"] if first else "", "problem": account["summary"],
                         "responsibility": "", "choice": "\n\n".join(account["decisions"]), "alternative": "", "cost": "",
                         "reason": account["aim"], "action": account["contribution"], "after": account["outcome"],
                         "shared": account["sharedCredit"], "limit": "\n".join(account["limits"]), "context": complete,
                         "openQuestions": "\n".join(account["questions"]), "scopeTopic": "", "privateNotes": "",
                         "publicLink": "", "share": False, "sources": [copy.deepcopy(source_map[r]) for r in account["sourceRefs"]],
                         "feedback": [], "image": image_view(first) if first else None,
                         "images": [image_view(artifact) for artifact in artifacts[1:]]})
    draft = {"schema": "career-notebook/v1", "id": "context-" + fingerprint[:24],
             "updatedAt": int(datetime.fromisoformat(packet["updatedAt"]).replace(tzinfo=timezone.utc).timestamp() * 1000),
             "synthetic": bool(packet.get("synthetic")), "profile": {"name": packet["person"]["name"],
             "heading": "", "intro": packet["person"]["overview"], "focus": ""}, "accounts": accounts,
             "directions": [], "shareIntro": False}
    if companion is not None:
        draft["quarters"] = [{**{k: copy.deepcopy(v) for k, v in q.items() if k not in {"sourceRefs", "questions"}},
                              "questions": "\n".join(q["questions"]),
                              "sources": [copy.deepcopy(source_map[r]) for r in q["sourceRefs"]]} for q in companion["quarters"]]
    return draft


def validate_introductions(options, packet=None):
    if not isinstance(options, list) or not 1 <= len(options) <= 6:
        raise ValueError("Introductions must be a list of one to six options")
    ids = set()
    sources = {s["id"] for s in packet["sources"]} if packet else None
    for option in options:
        context_renderer.keys(option, ["id", "title", "text", "sourceRefs"], "Introduction")
        for field in ("id", "title", "text"):
            context_renderer.check_text(option.get(field), f"Introduction {field}")
            if not option[field].strip():
                raise ValueError(f"Introduction {field} must not be empty")
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}", option["id"]) or option["id"] in ids:
            raise ValueError("Introduction IDs must be unique and safe")
        ids.add(option["id"])
        refs = option.get("sourceRefs", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs) or len(set(refs)) != len(refs):
            raise ValueError("Introduction sourceRefs must be a list of unique source IDs")
        if sources is not None and set(refs) - sources:
            raise ValueError("Introduction sourceRefs must resolve to included sources")


def validate_overlay(draft):
    """Retain edits as a distinct layer, with the runtime's basic data contract."""
    if not isinstance(draft, dict) or draft.get("schema") != "career-notebook/v1":
        raise ValueError("Imported notebook has an unsupported editable payload")
    context_renderer.check_text(draft.get("id"), "Notebook ID", 200)
    if not isinstance(draft.get("profile"), dict) or not isinstance(draft.get("accounts"), list) or not isinstance(draft.get("directions"), list):
        raise ValueError("Imported notebook needs profile, accounts and directions")
    if not isinstance(draft.get("updatedAt"), (int, float)) or isinstance(draft["updatedAt"], bool) or not math.isfinite(draft["updatedAt"]):
        raise ValueError("Imported notebook needs a numeric update time")
    for field in ("name", "heading", "intro", "focus"):
        context_renderer.check_text(draft["profile"].get(field, ""), f"Notebook profile {field}")
    if "introOptions" in draft["profile"]:
        validate_introductions(draft["profile"]["introOptions"])
    ids = set()
    for account in draft["accounts"]:
        if not isinstance(account, dict):
            raise ValueError("Notebook accounts must be objects")
        for field in ACCOUNT_TEXT:
            context_renderer.check_text(account.get(field, ""), f"Notebook account {field}", 24 * 1024 * 1024)
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,99}", account.get("id", "")) or account["id"] in ids:
            raise ValueError("Notebook account IDs must be unique and safe")
        ids.add(account["id"])
        if not isinstance(account.get("sources"), list) or not isinstance(account.get("feedback"), list):
            raise ValueError("Notebook accounts need sources and feedback lists")
        if not isinstance(account.get("images", []), list):
            raise ValueError("Additional notebook images must be a list")
        for image in ([account["image"]] if account.get("image") is not None else []) + account.get("images", []):
            if not isinstance(image, dict) or not re.fullmatch(r"data:image/(?:png|jpeg|webp|gif);base64,[A-Za-z0-9+/=]+", str(image.get("data", ""))):
                raise ValueError("Notebook image must be an embedded PNG, JPEG, WebP or GIF")
            for field in ("alt", "caption", "date"):
                context_renderer.check_text(image.get(field, ""), f"Notebook image {field}")
        for collection, fields in [(account["sources"], ("title", "date", "url", "text", "kind", "originalKind")),
                                   (account["feedback"], ("quote", "relationship", "context", "date"))]:
            for item in collection:
                if not isinstance(item, dict):
                    raise ValueError("Notebook sources and feedback must contain objects")
                for field in fields:
                    context_renderer.check_text(item.get(field, ""), f"Notebook {field}", 24 * 1024 * 1024)


def fallback_html(packet, images, companion, draft):
    esc = html.escape
    def paragraph(text):
        return "".join("<p>" + esc(line) + "</p>" for line in text.split("\n\n") if line.strip())
    parts = ['<noscript id="career-context-fallback"><main><h1>' + esc(packet["person"]["name"]) + " — Career context</h1>"]
    if packet.get("synthetic"):
        parts.append("<p>Synthetic demo data. These accounts are fictional.</p>")
    parts.append("<p>Canonical source context · " + esc(packet["reviewStatus"]) + " · " + esc(packet["updatedAt"]) + "</p>")
    parts.append(paragraph(packet["person"]["overview"]))
    for line in packet["person"].get("background", []):
        parts.append(paragraph(line))
    if companion:
        parts.append("<section><h2>Quarterly work</h2>")
        for q in companion["quarters"]:
            parts.append('<article id="quarter-' + q["id"] + '"><h3>' + esc(q["period"] + " · " + q["title"]) + "</h3>")
            for label, value in [("Focus", q["focus"]), ("Work", "\n\n".join(q["actions"])), ("Pressure", q["tension"]), ("Approach", q["style"]), ("Questions", "\n\n".join(q["questions"]))]:
                if value:
                    parts.append("<h4>" + label + "</h4>" + paragraph(value))
            parts.append('<p><a href="#canonical-account-' + q["accountId"] + '">Read the linked work account</a></p>')
            parts.append('<p>Sources: ' + " · ".join('<a href="#canonical-source-' + ref + '">' + esc(next(s["label"] for s in packet["sources"] if s["id"] == ref)) + "</a>" for ref in q["sourceRefs"]) + "</p></article>")
        parts.append("</section>")
    for account in packet["accounts"]:
        parts.append('<article id="canonical-account-' + account["id"] + '"><h2>' + esc(account["title"]) + "</h2>" + paragraph(account["period"]))
        for label, text in context_sections(account):
            if text:
                parts.append("<h3>" + label + "</h3>" + paragraph(text))
        for artifact in account.get("artifacts", []):
            parts.append('<figure><img id="' + artifact["embeddedId"] + '" src="' + images[artifact["id"]] + '" alt="' + esc(artifact["title"], quote=True) + '" style="max-width:100%;height:auto"><figcaption>' + esc(artifact["caption"]) + "</figcaption></figure>")
        parts.append('<p>Sources: ' + " · ".join('<a href="#canonical-source-' + ref + '">' + esc(next(s["label"] for s in packet["sources"] if s["id"] == ref)) + "</a>" for ref in account["sourceRefs"]) + "</p></article>")
    parts.append("<section><h2>Included source context</h2>")
    for source in packet["sources"]:
        parts.append('<article id="canonical-source-' + source["id"] + '"><h3>' + esc(source["label"]) + "</h3>" + paragraph(source["kind"]) + paragraph(source["content"]) + paragraph(source["scope"]) + paragraph(source.get("date", "")) + paragraph(source.get("locator", "")) + "</article>")
    parts.append("</section>")
    baseline = draft_from_packet(packet, images, companion)
    if any(draft.get(key) != baseline.get(key) for key in ("profile", "accounts", "directions", "quarters")):
        parts.append("<section><h2>Notebook working draft</h2><p>These saved notebook edits are separate from the canonical source context above.</p>")
        parts.append(paragraph(draft["profile"].get("intro", "")))
        if draft["profile"].get("introOptions"):
            parts.append("<section><h3>Alternative introductions</h3>")
            for option in draft["profile"]["introOptions"]:
                parts.append("<article><h4>" + esc(option["title"]) + "</h4>" + paragraph(option["text"]) + "</article>")
            parts.append("</section>")
        for account in draft["accounts"]:
            parts.append("<article><h3>" + esc(account.get("title", "Untitled account")) + "</h3>")
            for key in ("period", "problem", "responsibility", "choice", "alternative", "cost", "reason", "action", "after", "shared", "limit", "context", "openQuestions", "privateNotes"):
                if account.get(key):
                    parts.append("<h4>" + esc(key) + "</h4>" + paragraph(account[key]))
            for source in account["sources"]:
                parts.append("<h4>" + esc(source.get("title", "Source")) + "</h4>" + paragraph(source.get("text", "")))
            for feedback in account["feedback"]:
                parts.append("<blockquote>" + paragraph(feedback.get("quote", "")) + "</blockquote>" + paragraph(feedback.get("relationship", "")) + paragraph(feedback.get("context", "")))
            for image in ([account["image"]] if account.get("image") else []) + account.get("images", []):
                parts.append('<figure><img src="' + image["data"] + '" alt="' + esc(image.get("alt", ""), quote=True) + '" style="max-width:100%;height:auto"><figcaption>' + esc(image.get("caption", "")) + "</figcaption></figure>")
            parts.append("</article>")
        parts.append("</section>")
    parts.append("</main></noscript>")
    return "".join(parts)


def json_script(name, data):
    value = json.dumps(data, ensure_ascii=True).replace("<", "\\u003c").replace("&", "\\u0026")
    return '<script id="' + name + '" type="application/json">' + value + "</script>"


def render(source, destination, *, quarters=None, introductions=None, overwrite=True):
    source, destination = Path(source), Path(destination)
    packet, images = prepared_packet(source)
    imported = imported_payloads(source)
    companion = json.loads(Path(quarters).read_text(encoding="utf-8")) if quarters else imported.value("career-quarters-data")
    if companion is not None:
        validate_quarters(companion, packet)
    draft = imported.value("career-draft-data")
    if draft is None:
        draft = draft_from_packet(packet, images, companion)
    else:
        validate_overlay(draft)
        draft = copy.deepcopy(draft)
        if quarters:
            draft["quarters"] = draft_from_packet(packet, images, companion).get("quarters", [])
    if introductions:
        options = json.loads(Path(introductions).read_text(encoding="utf-8"))
        validate_introductions(options, packet)
        if options != draft["profile"].get("introOptions"):
            draft["profile"]["introOptions"] = options
            # A browser draft for the previous comparison must not hide new options.
            identity = json.dumps([draft["id"], options], sort_keys=True, ensure_ascii=True).encode()
            draft["id"] = "comparison-" + hashlib.sha256(identity).hexdigest()[:24]
    if draft["profile"].get("introOptions"):
        validate_introductions(draft["profile"]["introOptions"], packet)
    draft["synthetic"] = bool(packet.get("synthetic"))
    template = (SKILL / "assets/notebook.html").read_text(encoding="utf-8-sig")
    for name in ("career-context-data", "career-draft-data", "career-quarters-data"):
        template = re.sub(r'<script\b(?=[^>]*\bid\s*=\s*[\"\']' + name + r'[\"\'])[^>]*>.*?</script\s*>', "", template, flags=re.S | re.I)
    template = re.sub(r'<noscript\b(?=[^>]*\bid\s*=\s*[\"\']career-context-fallback[\"\'])[^>]*>.*?</noscript\s*>', "", template, flags=re.S | re.I)
    payload = json_script("career-context-data", packet) + json_script("career-draft-data", draft)
    if companion is not None:
        payload += json_script("career-quarters-data", companion)
    payload += fallback_html(packet, images, companion, draft)
    output, inserted = re.subn(r'(<body\b[^>]*>)', lambda m: m[1] + payload, template, count=1, flags=re.I)
    if not inserted:
        raise ValueError("Notebook asset needs a body element")
    if len(output.encode("utf-8")) > 24 * 1024 * 1024:
        raise ValueError("Notebook exceeds the portable 24 MiB limit; select fewer images")
    if destination.is_symlink():
        raise ValueError("Output must not be a symbolic link")
    fd, temporary = tempfile.mkstemp(dir=destination.parent, prefix=".career-notebook-", suffix=".tmp")
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(output.encode("utf-8"))
        if overwrite:
            os.replace(temporary, destination)
        else:
            os.link(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {"path": str(destination), "accounts": len(packet["accounts"]), "quarters": len(draft.get("quarters", [])),
            "sources": len(packet["sources"]), "bytes": len(output.encode("utf-8")), "sha256": hashlib.sha256(output.encode("utf-8")).hexdigest()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Career-context JSON or an existing HTML notebook")
    parser.add_argument("output", type=Path, help="HTML destination")
    parser.add_argument("--quarters", type=Path, help="Explicit career-quarters/v1 companion")
    parser.add_argument("--introductions", type=Path, help="Agent-authored introduction options as a JSON list")
    parser.add_argument("--force", action="store_true", help="Replace an existing output")
    args = parser.parse_args(argv)
    try:
        destination = args.output.expanduser().absolute()
        if destination.suffix.lower() not in {".html", ".htm"}:
            raise ValueError("Choose an output ending in .html or .htm")
        if destination.is_symlink() or (destination.exists() and not args.force):
            raise ValueError("Output is a symbolic link or already exists; use --force only for an existing file")
        if not destination.parent.is_dir():
            raise ValueError("Create the output folder first")
        result = render(args.input.expanduser().resolve(), destination, quarters=args.quarters, introductions=args.introductions, overwrite=args.force)
    except (ValueError, KeyError, TypeError, OSError) as error:
        parser.exit(2, f"Could not create the notebook: {error}\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
