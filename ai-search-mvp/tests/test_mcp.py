import json
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mcp_server import respond, check, TOOLS
from adapter import digest
from cli import load_fixture


class McpTests(unittest.TestCase):
    def test_stdio_roundtrip_and_boundary(self):
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "fixture-test", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "source_read", "arguments": {"case": "training", "source": "chat", "id": "chat:001"}}},
            {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "post_message", "arguments": {"case": "training"}}},
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "source_inventory", "arguments": {"case": "../private"}}},
        ]
        process = subprocess.run([sys.executable, str(ROOT / "mcp_server.py")], input="\n".join(json.dumps(x) for x in requests)+"\n", text=True, capture_output=True, timeout=20)
        self.assertEqual(process.returncode, 0, process.stderr)
        replies = [json.loads(x) for x in process.stdout.splitlines()]
        self.assertEqual(len(replies), 5)
        self.assertEqual(len(replies[1]["result"]["tools"]), 6)
        self.assertEqual(replies[2]["result"]["structuredContent"]["items"][0]["id"], "chat:001")
        self.assertTrue(replies[3]["result"]["isError"])
        self.assertTrue(replies[4]["result"]["isError"])

    def test_request_schema_rejects_extra_paths(self):
        schema = next(t for t in TOOLS if t["name"] == "research_run")["inputSchema"]
        with self.assertRaises(ValueError):
            check({"case": "training", "path": "../private"}, schema)
        with self.assertRaises(ValueError):
            check({"case": "training", "steps": 100000}, schema)

    def test_forged_review_is_rejected(self):
        reply = respond({"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "review_submit", "arguments": {"case": "training", "claim": "Unsupported", "limits": "", "evidence": [{"record_id": "chat:001", "hash": "wrong", "start": 0, "end": 5, "quote": "wrong"}]}}})
        self.assertTrue(reply["result"]["isError"])

    def test_audit_denies_private_workspace_and_answer_key_before_open(self):
        code = """
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from boundary import install
root=Path(sys.argv[1]); install(root)
blocked=0
for path in [root.parent/'private-sentinel-does-not-exist.txt',root/'fixtures'/'training.gold.json']:
 try: path.read_text()
 except PermissionError: blocked+=1
print(blocked)
"""
        process = subprocess.run([sys.executable, "-c", code, str(ROOT)], text=True, capture_output=True, timeout=10)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(process.stdout.strip(), "2")

    def test_rule_hash_remains_frozen_for_challenge(self):
        import hashlib
        gold = json.loads((ROOT / "fixtures" / "challenge.gold.json").read_text(encoding="utf-8"))
        self.assertEqual(hashlib.sha256((ROOT / "reviewer.py").read_bytes()).hexdigest(), gold["reviewer_hash_before_challenge"])

    def test_valid_review_saved_as_proposal_and_stale_revision_rejected(self):
        from mcp_server import execute
        scratch = ROOT / "runs" / "test-scratch" / "mcp"
        folder = scratch / "runs" / "training"
        folder.mkdir(parents=True, exist_ok=True)
        record = load_fixture("training")[0]["records"][0]
        result_path = folder / "result.json"
        review_path = folder / "model-reviews.json"
        result_path.write_text(json.dumps({"records": [record]}), encoding="utf-8")
        args = {"case": "training", "claim": "Contributor 01 proposed a queue experiment.", "limits": "Proposal only; this passage does not establish delivery.",
                "evidence": [{"record_id": record["id"], "hash": digest(record), "start": 0, "end": len(record["body"]), "quote": record["body"]}]}
        try:
            with patch('mcp_server.ROOT', scratch):
                result = execute("review_submit", args)
                self.assertEqual(result["state"], "needs_review")
                self.assertFalse(result["meaning_checked"])
                self.assertTrue(review_path.exists())
                args["evidence"][0]["hash"] = "old-revision"
                with self.assertRaises(ValueError):
                    execute("review_submit", args)
        finally:
            for path in [result_path, review_path]:
                if path.exists():
                    path.unlink()


if __name__ == "__main__":
    unittest.main()
