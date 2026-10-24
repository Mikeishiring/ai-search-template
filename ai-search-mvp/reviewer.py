"""Transparent lexical reviewer, not an LLM or a claim of semantic understanding.

Rules are fixed before the challenge run. Output is anchored candidate evidence.
Only explicit relationships connect records; shared names never merge projects.
"""
import re


RULES = {
    "proposal": r"\b(propos\w*|suggest\w*|my idea)\b",
    "scope_change": r"\b(narrow\w*|scope|brief|pilot only|one team only|not a company rollout)\b",
    "contribution": r"\b(built|implemented|coordinated|organised|organized|maintain\w*|wrote|authored)\b",
    "collaboration": r"\b(co-authored|collaborat\w*|pair\w*|credit|owned|responsible for)\b",
    "use": r"\b(i used|we used|used it again|ran it again|we ran)\b",
    "correction": r"\b(fix\w*|correct\w*|bug\w*|regression\w*)\b",
    "pause": r"\b(paused|postpon\w*|cancel\w*|retired|shelved)\b",
    "constraint": r"\b(depend\w*|budget|priority|priorities|blocked|capacity)\b",
    "praise": r"\b(thank\w*|excellent|helpful|great work)\b",
}
STAGES = ["proposal", "scope_change", "contribution", "use", "correction", "pause"]


def inspect(record):
    body = record["body"]
    findings = []
    for sentence in re.finditer(r"[^.!?\n]+(?:[.!?]|$)", body):
        quote = sentence.group().strip()
        start = sentence.start() + len(sentence.group()) - len(sentence.group().lstrip())
        for category, rule in RULES.items():
            if re.search(rule, quote, re.I):
                findings.append({"category": category, "record_id": record["id"],
                                 "start": start, "end": start + len(quote), "quote": quote,
                                 "speaker": record["author"], "status": "candidate",
                                 "limit": "Lexical signal; quotation preserves attribution and negation. Human or model interpretation still required."})
    return findings


def validate_finding(finding, records):
    r = records.get(finding.get("record_id"))
    if r is None:
        raise ValueError("Unknown evidence record")
    start, end = finding.get("start"), finding.get("end")
    if not isinstance(start, int) or not isinstance(end, int) or not 0 <= start < end <= len(r["body"]):
        raise ValueError("Invalid evidence span")
    if r["body"][start:end] != finding.get("quote"):
        raise ValueError("Evidence quote does not match retained source")


def components(records):
    graph = {r["id"]: set() for r in records}
    for r in records:
        related = [r.get("parent"), r.get("repost_of")] + [x["id"] for x in r.get("links", [])]
        for target in related:
            if target in graph:
                graph[r["id"]].add(target)
                graph[target].add(r["id"])
    groups, seen = [], set()
    for key in sorted(graph):
        if key in seen:
            continue
        pending, group = [key], []
        while pending:
            node = pending.pop()
            if node in seen:
                continue
            seen.add(node)
            group.append(node)
            pending.extend(graph[node] - seen)
        groups.append(sorted(group))
    return groups
