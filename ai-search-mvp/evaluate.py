"""Evaluator only. The runner never imports this module or loads an answer key."""
import json
from pathlib import Path

from adapter import SyntheticAdapter
from reviewer import inspect


def evaluate(corpus, scope, result, gold):
    baseline_adapter = SyntheticAdapter(corpus)
    baseline = {}
    for source in scope["sources"]:
        for record in baseline_adapter.call("search_records", source, query=scope["query"], horizon=scope["horizon"])["items"]:
            baseline[record["id"]] = record
    baseline_signals = [f for r in baseline.values() for f in inspect(r)]
    actual = {r["id"] for r in result["records"]}
    signals = {(f["record_id"], f["category"]) for f in result["findings"]}
    basic = {(f["record_id"], f["category"]) for f in baseline_signals}
    expected = set(gold["expected_records"])
    themes = [t | {"retrieved": t["record"] in actual,
                   "surfaced": (t["record"], t["category"]) in signals,
                   "baseline_retrieved": t["record"] in baseline,
                   "baseline_surfaced": (t["record"], t["category"]) in basic}
              for t in gold["themes"]]
    violations = []
    a, b = gold["must_not_merge"]
    if any(a in group and b in group for group in result["components"]):
        violations.append("Unrelated projects were merged")
    if any(c["review_state"] != "candidate_evidence_only" for c in result["coverage"]):
        violations.append("Lexical scanning was presented as semantic review")
    missing_attachment_visible = any(t["state"] == "blocked" and t["args"].get("id") == gold["unavailable_attachment"] for t in result["tasks"])
    if not missing_attachment_visible:
        violations.append("Missing original attachment was not disclosed")
    missed = [t["name"] for t in themes if not t["surfaced"]]
    return {"fixture": gold["label"], "expected_records": len(expected),
            "retrieved_expected": len(expected & actual), "missing_records": sorted(expected - actual),
            "out_of_scope_records": sorted(actual - expected),
            "baseline_records": len(expected & set(baseline)),
            "baseline_calls": len(baseline_adapter.calls), "runner_receipts": result["receipts"],
            "themes": themes, "surfaced": sum(t["surfaced"] for t in themes),
            "baseline_surfaced": sum(t["baseline_surfaced"] for t in themes),
            "missed": missed, "violations": violations,
            "verdict": "NOT READY for autonomous narrative: rule-based signals need semantic review",
            "method": "Program-blind answer key; fixture author also wrote the runner. Not an independently blind benchmark. No external model calls.",
            "harsh_review": [
                "Retrieving every record is a coverage result, not proof of understanding.",
                "Lexical signals preserve quotes but do not establish who did what or resolve contradictions.",
                "The baseline is a deliberately shallow single-query search, not a state-of-the-art retrieval baseline.",
                "The synthetic corpus is small and clean; real exports, permissions, retries and messy identity resolution remain untested.",
                "The critic is a deterministic gap detector. It cannot independently reason about fairness or causality.",
                "Implicit links and unfamiliar wording can be missed even after the correct record has been retrieved.",
                "No live MCP, calendar, private archive, external model or network operation is used.",
            ]}


def evaluate_file(root: Path, case: str):
    fixtures = root / "fixtures"
    load = lambda p: json.loads(p.read_text(encoding="utf-8"))
    result = load(root / "runs" / case / "result.json")
    score = evaluate(load(fixtures / f"{case}.corpus.json"), load(fixtures / f"{case}.scope.json"), result, load(fixtures / f"{case}.gold.json"))
    (root / "runs" / case / "evaluation.json").write_text(json.dumps(score, indent=2), encoding="utf-8")
    return score
