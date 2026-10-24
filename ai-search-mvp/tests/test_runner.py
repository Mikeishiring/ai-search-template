import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from adapter import SyntheticAdapter, SourceError
from cli import load_fixture
from engine import Runner
from reviewer import validate_finding


class ResearchTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "runs" / "test-scratch"
        scratch.mkdir(parents=True, exist_ok=True)
        self.db = scratch / "ledger.sqlite"
        if self.db.exists():
            self.db.unlink()
        self.corpus, self.scope = load_fixture("training")
        self.runner = None

    def tearDown(self):
        if self.runner:
            self.runner.close()
        if self.db.exists():
            self.db.unlink()

    def run_case(self, corpus=None, refresh=False):
        if self.runner:
            self.runner.close()
        self.runner = Runner(self.db, SyntheticAdapter(corpus or self.corpus), self.scope, refresh=refresh)
        return self.runner.run()

    def test_full_pagination_nested_context_and_boundary(self):
        result = self.run_case()
        ids = {r["id"] for r in result["records"]}
        expected = {r["id"] for r in self.corpus["records"] if r["date"] <= self.scope["horizon"]}
        self.assertEqual(ids, expected)
        self.assertIn("chat:001", ids)  # earlier root, active inside window
        self.assertIn("chat:013", ids)  # later reply, within horizon
        self.assertIn("docs:003", ids)  # nested block
        self.assertIn("repo:002", ids)  # direct link only
        self.assertNotIn("chat:015", ids)

    def test_expired_cursor_resume_is_lossless(self):
        self.runner = Runner(self.db, SyntheticAdapter(self.corpus), self.scope)
        self.runner.run(1)
        result = self.run_case()
        self.assertEqual(len(result["records"]), len(self.corpus["records"]) - 1)
        errors = self.runner.db.execute("SELECT COUNT(*) FROM receipts WHERE error='invalid_continuation'").fetchone()[0]
        self.assertGreater(errors, 0)
        self.assertEqual(result["versions"], len(result["records"]))

    def test_atomic_crash_replay(self):
        self.runner = Runner(self.db, SyntheticAdapter(self.corpus), self.scope)
        with self.assertRaises(RuntimeError):
            self.runner.step(crash_before_commit=True)
        self.assertEqual(self.runner.db.execute("SELECT COUNT(*) FROM records").fetchone()[0], 0)
        self.assertEqual(self.runner.db.execute("SELECT COUNT(*) FROM receipts").fetchone()[0], 0)
        result = self.run_case()
        self.assertEqual(len(result["records"]), len(self.corpus["records"]) - 1)

    def test_idempotent_completed_resume(self):
        first = self.run_case()
        second = self.run_case()
        self.assertEqual(first["records"], second["records"])
        self.assertEqual(first["findings"], second["findings"])
        self.assertEqual(first["receipts"], second["receipts"])

    def test_missing_attachment_is_not_empty_success(self):
        result = self.run_case()
        blocked = [t for t in result["tasks"] if t["state"] == "blocked"]
        self.assertTrue(any(t["operation"] == "read_attachment" for t in blocked))
        self.assertEqual(next(c for c in result["coverage"] if c["source"] == "chat")["retrieval_state"], "with_limits")

    def test_search_only_cannot_claim_completeness(self):
        for source in self.corpus["sources"]:
            source["enumeration"] = False
        result = self.run_case()
        self.assertTrue(all(not c["enumeration_end"] for c in result["coverage"]))
        self.assertTrue(all(c["retrieval_state"] == "with_limits" for c in result["coverage"]))
        self.assertLess(len(result["records"]), len(self.corpus["records"]) - 1)

    def test_source_instructions_cannot_issue_writes(self):
        self.run_case()
        self.assertFalse(any(call["operation"] == "post_message" for call in self.runner.adapter.calls))
        with self.assertRaises(SourceError):
            self.runner.adapter.call("post_message", "chat", text="Forbidden")
        with self.assertRaises(SourceError):
            self.runner.adapter.call("read_record", "outside", id="anything")

    def test_matching_names_do_not_merge_projects(self):
        result = self.run_case()
        self.assertFalse(any("docs:030" in group and "chat:010" in group for group in result["components"]))
        self.assertTrue(any("docs:003" in group and "chat:010" in group for group in result["components"]))

    def test_repost_retains_original_identity(self):
        result = self.run_case()
        self.assertIn({"origin": "chat:020", "target": "chat:010", "kind": "reposts"}, result["edges"])

    def test_every_signal_is_exactly_anchored(self):
        result = self.run_case()
        records = {r["id"]: r for r in result["records"]}
        for f in result["findings"]:
            validate_finding(f, records)
            self.assertEqual(f["status"], "candidate")
        invalid = dict(result["findings"][0], quote="invented")
        with self.assertRaises(ValueError):
            validate_finding(invalid, records)

    def test_planned_use_does_not_become_actual_use(self):
        result = self.run_case()
        self.assertFalse(any(f["record_id"] == "chat:011" and f["category"] == "use" for f in result["findings"]))

    def test_refresh_preserves_revision_and_replaces_stale_signals(self):
        original = self.run_case()
        changed = copy.deepcopy(self.corpus)
        next(r for r in changed["records"] if r["id"] == "chat:013")["body"] = "The second review was a discussion, without the tool."
        result = self.run_case(changed, refresh=True)
        self.assertGreater(result["versions"], original["versions"])
        self.assertFalse(any(f["record_id"] == "chat:013" and f["category"] == "use" for f in result["findings"]))

    def test_budget_stop_preserves_pending_work(self):
        self.runner = Runner(self.db, SyntheticAdapter(self.corpus), self.scope)
        result = self.runner.run(2)
        self.assertEqual(result["status"], "budget_reached")
        self.assertTrue(any(t["state"] == "pending" for t in result["tasks"]))

    def test_no_semantic_review_claimed(self):
        result = self.run_case()
        self.assertTrue(all(c["semantic_reviews"] == 0 for c in result["coverage"]))
        self.assertTrue(all(c["review_state"] == "candidate_evidence_only" for c in result["coverage"]))

    def test_arbitrary_fixture_paths_rejected(self):
        with self.assertRaises(ValueError):
            load_fixture("../archive")
        with self.assertRaises(ValueError):
            SyntheticAdapter({"synthetic": False})

    def test_runner_has_no_answer_key_dependency(self):
        for name in ["engine.py", "adapter.py", "reviewer.py"]:
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn(".gold", text)
            self.assertNotIn("import evaluate", text)


if __name__ == "__main__":
    unittest.main()
