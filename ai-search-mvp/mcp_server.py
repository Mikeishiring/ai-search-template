"""Minimal stdio MCP bridge for an AI host. Synthetic data only; no paid API key.

The host supplies the model. This server does not pretend its lexical reviewer is AI.
Messages are newline-delimited JSON-RPC; stdout is reserved for the protocol.
"""
import json
import sys
from pathlib import Path

from adapter import SyntheticAdapter, digest
from boundary import install
from cli import ROOT, load_fixture
from engine import Runner
from reviewer import validate_finding

CASES = {"type": "string", "enum": ["training", "challenge", "search_only", "semantic"]}


def tool(name, description, properties, required, writes=False):
    return {"name": name, "description": description,
            "inputSchema": {"type": "object", "properties": {"case": CASES, **properties},
                            "required": ["case", *required], "additionalProperties": False},
            "annotations": {"readOnlyHint": not writes, "destructiveHint": False, "openWorldHint": False}}


TOOLS = [
    tool("research_run", "Run or resume bounded synthetic research. Writes only the local synthetic ledger. Does not perform semantic review.", {"steps": {"type": "integer", "minimum": 1, "maximum": 1000}}, [], True),
    tool("research_status", "Return saved source coverage and unresolved tasks. Search and rule scanning are not full review.", {}, []),
    tool("source_inventory", "List the declared synthetic sources and read capabilities.", {}, []),
    tool("source_read", "Read one original synthetic record. Returns a revision hash for anchoring review.", {"source": {"type": "string"}, "id": {"type": "string"}}, ["source", "id"]),
    tool("source_context", "Read one page of replies or nested blocks, with a durable inclusive recovery boundary.", {"source": {"type": "string"}, "id": {"type": "string"}, "after": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2}}, ["source", "id"]),
    tool("review_submit", "Save a model-proposed claim with exact evidence spans and revision hashes. Validates provenance, not truth; saved as needs_review.",
         {"claim": {"type": "string"}, "limits": {"type": "string"}, "evidence": {"type": "array", "minItems": 1,
          "items": {"type": "object", "properties": {"record_id": {"type": "string"}, "hash": {"type": "string"}, "start": {"type": "integer"}, "end": {"type": "integer"}, "quote": {"type": "string"}},
                    "required": ["record_id", "hash", "start", "end", "quote"], "additionalProperties": False}}}, ["claim", "limits", "evidence"], True),
]


def check(value, schema):
    kind = schema.get("type")
    valid = {"object": isinstance(value, dict), "array": isinstance(value, list),
             "string": isinstance(value, str), "integer": isinstance(value, int) and not isinstance(value, bool)}
    if not valid.get(kind, False):
        raise ValueError("Invalid argument type")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Unknown synthetic case")
    if kind == "integer" and not schema.get("minimum", -float("inf")) <= value <= schema.get("maximum", float("inf")):
        raise ValueError("Argument outside bounded range")
    if kind == "object":
        if not set(schema.get("required", [])).issubset(value) or set(value) - set(schema["properties"]):
            raise ValueError("Missing or extra arguments")
        for k, v in value.items():
            check(v, schema["properties"][k])
    if kind == "array":
        if not schema.get("minItems", 0) <= len(value) <= schema.get("maxItems", 10000):
            raise ValueError("Invalid item count")
        for v in value:
            check(v, schema["items"])


def execute(name, args):
    definition = next((t for t in TOOLS if t["name"] == name), None)
    if not definition:
        raise ValueError("Tool is not in the read/local-ledger allowlist")
    check(args, definition["inputSchema"])
    case = args["case"]
    corpus, scope = load_fixture(case)
    adapter = SyntheticAdapter(corpus)
    if name == "source_inventory":
        return {"synthetic": True, "scope": scope, "sources": [adapter.call("describe_access", s) for s in scope["sources"]]}
    if name in {"source_read", "source_context"}:
        params = {"id": args["id"]}
        if name == "source_context":
            params.update(horizon=scope["horizon"], after=args.get("after"))
        result = adapter.call("read_record" if name == "source_read" else "read_context", args["source"], **params)
        result["items"] = [r | {"record_hash": digest(r)} for r in result["items"] if r["date"] <= scope["horizon"]]
        return result
    folder = ROOT / "runs" / case
    folder.mkdir(parents=True, exist_ok=True)
    if name == "review_submit":
        if not args["claim"].strip():
            raise ValueError("Claim cannot be empty")
        current = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        records = {r["id"]: r for r in current["records"]}
        for evidence in args["evidence"]:
            validate_finding(evidence, records)
            record = records[evidence["record_id"]]
            live = adapter.call("read_record", record["source"], id=record["id"])["items"][0]
            if evidence["hash"] != digest(record) or evidence["hash"] != digest(live):
                raise ValueError("Evidence revision changed; re-read before submitting")
        payload = {"claim": args["claim"], "limits": args["limits"], "evidence": args["evidence"], "state": "needs_review", "provenance_checked": True, "meaning_checked": False}
        claim_id = digest(payload)
        path = folder / "model-reviews.json"
        reviews = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        reviews[claim_id] = payload
        staged = path.with_suffix(".tmp")
        staged.write_text(json.dumps(reviews, indent=2), encoding="utf-8")
        staged.replace(path)
        return {"claim_id": claim_id, "state": "needs_review", "provenance_checked": True, "meaning_checked": False}
    if name == "research_status":
        if not (folder / "result.json").exists():
            return {"state": "not_started"}
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
    else:
        runner = Runner(folder / "ledger.sqlite", adapter, scope)
        try:
            result = runner.run(args.get("steps", 100))
            result["input_files"] = [f"fixtures/{'training' if case == 'search_only' else case}.{suffix}.json" for suffix in ["corpus", "scope"]]
            (folder / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        finally:
            runner.close()
    return {"status": result["status"], "coverage": result["coverage"], "candidate_findings": result["findings"],
            "record_ids": [r["id"] for r in result["records"]], "unresolved_tasks": [t for t in result["tasks"] if t["state"] != "done"]}


def respond(message):
    if "id" not in message:
        return None
    id = message["id"]
    try:
        method = message["method"]
        if method == "initialize":
            result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "synthetic-research-mvp", "version": "0.1.0"}}
        elif method == "ping":
            result = {}
        elif method == "tools/list":
            result = {"tools": TOOLS}
        elif method == "tools/call":
            params = message["params"]
            try:
                data = execute(params["name"], params.get("arguments", {}))
                result = {"content": [{"type": "text", "text": json.dumps(data)}], "structuredContent": data, "isError": False}
            except Exception as error:
                # Avoid leaking OS paths or source data in protocol exceptions.
                result = {"content": [{"type": "text", "text": f"Request rejected ({type(error).__name__}); check arguments, scope and evidence anchors."}], "isError": True}
        else:
            return {"jsonrpc": "2.0", "id": id, "error": {"code": -32601, "message": "Method not found"}}
        return {"jsonrpc": "2.0", "id": id, "result": result}
    except (KeyError, TypeError):
        return {"jsonrpc": "2.0", "id": id, "error": {"code": -32600, "message": "Invalid request"}}


if __name__ == "__main__":
    install(ROOT)
    for line in sys.stdin:
        try:
            message = json.loads(line)
            reply = respond(message)
        except (ValueError, TypeError):
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}
        if reply is not None:
            print(json.dumps(reply), flush=True)
