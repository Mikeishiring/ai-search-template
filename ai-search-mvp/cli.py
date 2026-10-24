"""Run only the bundled synthetic fixtures. Python standard library only."""
import argparse
import json
from pathlib import Path

from adapter import SyntheticAdapter
from engine import Runner

ROOT = Path(__file__).resolve().parent


def load_fixture(case):
    if case not in {"training", "challenge", "search_only", "semantic"}:
        raise ValueError("Only bundled fixture names are accepted")
    base = "training" if case == "search_only" else case
    corpus = json.loads((ROOT / "fixtures" / f"{base}.corpus.json").read_text(encoding="utf-8"))
    scope = json.loads((ROOT / "fixtures" / f"{base}.scope.json").read_text(encoding="utf-8"))
    if case == "search_only":
        for source in corpus["sources"]:
            source["enumeration"] = False
    return corpus, scope


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="Run or resume a synthetic research pass")
    run.add_argument("case", choices=["training", "challenge", "search_only", "semantic"])
    run.add_argument("--steps", type=int, default=1000)
    run.add_argument("--refresh", action="store_true", help="Re-read the fixture, retaining source revisions")
    ev = sub.add_parser("evaluate", help="Read the separate answer key only after a run")
    ev.add_argument("case", choices=["training", "challenge"])
    sub.add_parser("report", help="Build the local HTML from saved synthetic results")
    args = parser.parse_args()
    if args.command == "run":
        if args.steps < 1:
            parser.error("steps must be positive")
        from boundary import install
        input_files = install(ROOT)
        corpus, scope = load_fixture(args.case)
        folder = ROOT / "runs" / args.case
        folder.mkdir(parents=True, exist_ok=True)
        runner = Runner(folder / "ledger.sqlite", SyntheticAdapter(corpus), scope, refresh=args.refresh)
        try:
            result = runner.run(args.steps)
            result["input_files"] = sorted(input_files)
            (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
            print(json.dumps({"case": args.case, "status": result["status"], "records": len(result["records"]), "receipts": result["receipts"], "pending": sum(t["state"] == "pending" for t in result["tasks"])}))
        finally:
            runner.close()
    elif args.command == "evaluate":
        from evaluate import evaluate_file
        score = evaluate_file(ROOT, args.case)
        print(json.dumps({k: score[k] for k in ["fixture", "retrieved_expected", "expected_records", "surfaced", "baseline_surfaced", "missed", "violations", "verdict"]}, indent=2))
    else:
        from report import build
        print(build(ROOT))


if __name__ == "__main__":
    main()
