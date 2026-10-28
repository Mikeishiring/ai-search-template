"""Notebook adaptation, explicit quarter evidence and portable roundtrips."""
import base64
import copy
import importlib.util
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/career-context-sheet/scripts/render_notebook.py"
spec = importlib.util.spec_from_file_location("notebook_renderer", SCRIPT)
notebook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(notebook)


class NotebookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.skill = self.folder / "isolated skill"
        (self.skill / "assets").mkdir(parents=True)
        self.template = self.skill / "assets/notebook.html"
        self.template.write_text('<!doctype html><html><head><title>Notebook</title></head><body><div id="app"></div></body></html>', encoding="utf-8")
        self.patch = patch.object(notebook, "SKILL", self.skill)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.packet = json.loads((ROOT / "examples/career-context.json").read_text(encoding="utf-8"))
        self.source = self.folder / "context.json"
        self.output = self.folder / "notebook.html"
        self.companion = {"schema": "career-quarters/v1", "synthetic": True, "quarters": [{
            "id": "2030-Q1", "period": "2030 Q1", "title": "Clarifying the handoff", "focus": "Agree who owns each request.",
            "actions": ["Mapped the recurring handoffs.", "Trialled a shared review."], "tension": "Responsibilities were unclear.",
            "style": "Made the next owner explicit.", "questions": ["Which parts remained in use?"],
            "sourceRefs": [self.packet["sources"][0]["id"]], "accountId": self.packet["accounts"][0]["id"]}]}
        self.quarters = self.folder / "quarters.json"
        self.save()

    def save(self):
        self.source.write_text(json.dumps(self.packet), encoding="utf-8")
        self.quarters.write_text(json.dumps(self.companion), encoding="utf-8")

    def payload(self, name="career-draft-data", path=None):
        reader = notebook.imported_payloads(path or self.output)
        return reader.value(name)

    def test_packet_and_complete_account_survive_adaptation(self):
        notebook.render(self.source, self.output)
        self.assertEqual(notebook.context_renderer.load_packet(self.output), self.packet)
        draft = self.payload()
        self.assertEqual(draft["schema"], "career-notebook/v1")
        self.assertTrue(draft["synthetic"])
        self.assertFalse(draft["shareIntro"])
        self.assertNotIn("quarters", draft)
        for original, account in zip(self.packet["accounts"], draft["accounts"]):
            self.assertEqual(account["id"], original["id"])
            self.assertEqual(account["problem"], original["summary"])
            self.assertEqual(account["shared"], original["sharedCredit"])
            self.assertEqual(account["after"], original["outcome"])
            for label, text in notebook.context_sections(original):
                if text:
                    self.assertIn(text, account["context"], label)
            self.assertEqual(len(account["sources"]), len(original["sourceRefs"]))
            self.assertFalse(account["share"])
        markup = self.output.read_text(encoding="utf-8")
        self.assertIn('<noscript id="career-context-fallback">', markup)
        self.assertNotIn("Notebook working draft</h2>", markup)

    def test_no_change_rebuild_is_canonical_and_identity_is_stable(self):
        notebook.render(self.source, self.output)
        rebuilt = self.folder / "rebuilt.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.output.read_bytes(), rebuilt.read_bytes())
        first_id = self.payload()["id"]
        other = self.folder / "other-input.json"
        other.write_bytes(self.source.read_bytes())
        notebook.render(other, rebuilt)
        self.assertEqual(self.payload(path=rebuilt)["id"], first_id)
        self.packet["accounts"][0]["summary"] += " A corrected account."
        self.save()
        notebook.render(self.source, rebuilt)
        self.assertNotEqual(self.payload(path=rebuilt)["id"], first_id)

    def test_source_kind_and_scope_survive_reader_grouping(self):
        source = self.packet["sources"][0]
        source["kind"] = "archive_summary"
        source["scope"] = "Assistant summary; the original is not included."
        self.save()
        notebook.render(self.source, self.output, quarters=self.quarters)
        draft = self.payload()
        for adapted in (draft["accounts"][0]["sources"][0], draft["quarters"][0]["sources"][0]):
            self.assertEqual(adapted["kind"], "record")
            self.assertEqual(adapted["originalKind"], "archive_summary")
            self.assertIn(source["scope"], adapted["text"])
        rebuilt = self.folder / "source-kind-again.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.payload(path=rebuilt), draft)

    def test_quarters_require_explicit_companion_and_keep_resolving_evidence(self):
        notebook.render(self.source, self.output, quarters=self.quarters)
        draft = self.payload()
        quarter = draft["quarters"][0]
        self.assertEqual(quarter["id"], "2030-Q1")
        self.assertEqual(quarter["questions"], "Which parts remained in use?")
        self.assertEqual(quarter["accountId"], self.packet["accounts"][0]["id"])
        self.assertIn(self.packet["sources"][0]["content"], quarter["sources"][0]["text"])
        self.assertEqual(self.payload("career-quarters-data"), self.companion)
        rebuilt = self.folder / "quarter-rebuild.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.output.read_bytes(), rebuilt.read_bytes())

    def test_invalid_quarters_do_not_replace_existing_output(self):
        for field, value in [("accountId", "not-included"), ("sourceRefs", ["not-included"]),
                             ("period", "2030 Q2"), ("id", "sometime"), ("questions", "not a list")]:
            with self.subTest(field=field):
                bad = copy.deepcopy(self.companion)
                bad["quarters"][0][field] = value
                self.quarters.write_text(json.dumps(bad), encoding="utf-8")
                self.output.write_text("Existing work", encoding="utf-8")
                with self.assertRaises(ValueError):
                    notebook.render(self.source, self.output, quarters=self.quarters)
                self.assertEqual(self.output.read_text(), "Existing work")

    def test_saved_notebook_edits_roundtrip_without_rewriting_canonical_packet(self):
        notebook.render(self.source, self.output)
        draft = self.payload()
        draft["accounts"][0]["action"] = "A later correction in the notebook."
        draft["accounts"][0]["sources"].append({"title": "Correction", "text": "My later recollection.", "date": "", "url": "", "kind": "recollection"})
        draft["updatedAt"] += 1
        markup = self.output.read_text(encoding="utf-8")
        markup = re.sub(r'<script id="career-draft-data" type="application/json">.*?</script>', lambda _: notebook.json_script("career-draft-data", draft), markup, flags=re.S)
        self.output.write_text(markup, encoding="utf-8")
        rebuilt = self.folder / "edited.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.payload(path=rebuilt), draft)
        self.assertEqual(notebook.context_renderer.load_packet(rebuilt), self.packet)
        fallback = re.search(r'<noscript id="career-context-fallback">(.*?)</noscript>', rebuilt.read_text(encoding="utf-8"), re.S)[1]
        self.assertIn("A later correction in the notebook.", fallback)
        self.assertIn("My later recollection.", fallback)
        second = self.folder / "edited-again.html"
        notebook.render(rebuilt, second)
        self.assertEqual(rebuilt.read_bytes(), second.read_bytes())

    def test_all_artifacts_retain_bytes_hashes_and_inline_previews(self):
        fixtures = [("first", "png", "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aEkwAAAAASUVORK5CYII="),
                    ("second", "gif", "R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7")]
        artifacts = []
        for name, ext, data in fixtures:
            (self.folder / (name + "." + ext)).write_bytes(base64.b64decode(data))
            artifacts.append({"id": name, "title": name + " synthetic image", "caption": "Format fixture, not career evidence.", "file": name + "." + ext})
        self.packet["accounts"][0]["artifacts"] = artifacts
        self.save()
        notebook.render(self.source, self.output)
        canonical = notebook.context_renderer.load_packet(self.output)
        account = self.payload()["accounts"][0]
        self.assertTrue(account["image"]["data"].startswith("data:image/png;"))
        self.assertEqual(len(account["images"]), 1)
        self.assertTrue(account["images"][0]["data"].startswith("data:image/gif;"))
        for artifact, (_, ext, data) in zip(canonical["accounts"][0]["artifacts"], fixtures):
            self.assertNotIn("file", artifact)
            self.assertEqual(notebook.context_renderer.image_data(artifact, self.folder)[1], base64.b64decode(data))
            self.assertTrue(artifact["sha256"])
        rebuilt = self.folder / "images-again.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.output.read_bytes(), rebuilt.read_bytes())

    def test_hostile_source_text_is_inert_in_both_payloads_and_fallback(self):
        hostile = '</script><script>window.injected=true</script><img src=x onerror="alert(1)">'
        self.packet["accounts"][0]["summary"] = hostile
        self.packet["sources"][0]["content"] = hostile
        self.save()
        notebook.render(self.source, self.output)
        markup = self.output.read_text(encoding="utf-8")
        self.assertNotIn(hostile, markup)
        self.assertIn("&lt;/script&gt;", markup)
        self.assertEqual(notebook.context_renderer.load_packet(self.output), self.packet)
        self.assertEqual(self.payload()["accounts"][0]["problem"], hostile)

    def test_combined_context_larger_than_an_individual_field_still_roundtrips(self):
        self.packet["accounts"][0]["context"] = "Context detail. " * 6000
        self.packet["accounts"][0]["contribution"] = "My contribution. " * 5500
        self.packet["sources"][0]["scope"] = "Scope qualification. " * 4500
        self.save()
        notebook.render(self.source, self.output)
        self.assertGreater(len(self.payload()["accounts"][0]["context"]), 100000)
        rebuilt = self.folder / "long-again.html"
        notebook.render(self.output, rebuilt)
        self.assertEqual(self.output.read_bytes(), rebuilt.read_bytes())

    def test_isolated_direct_renderer_needs_no_repository_and_replacement_is_explicit(self):
        scripts = self.skill / "scripts"
        scripts.mkdir()
        for name in ("render_notebook.py", "render_context.py"):
            shutil.copyfile(SCRIPT.with_name(name), scripts / name)
        def command(*args):
            return subprocess.run([sys.executable, "-I", str(scripts / "render_notebook.py"), str(self.source), str(self.output), *args], cwd=self.folder, capture_output=True, text=True, timeout=20)
        result = command("--quarters", str(self.quarters))
        self.assertEqual(result.returncode, 0, result.stderr)
        before = self.output.read_bytes()
        result = command()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.output.read_bytes(), before)
        result = command("--force")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_asset_payload_placeholders_are_replaced_once(self):
        self.template.write_text('<html><body><script type="application/json" id="career-draft-data">{}</script><script id="career-context-data" type="application/json">{}</script><noscript id="career-context-fallback">Old fallback</noscript></body></html>', encoding="utf-8")
        notebook.render(self.source, self.output)
        markup = self.output.read_text(encoding="utf-8")
        self.assertEqual(markup.count('id="career-draft-data"'), 1)
        self.assertEqual(markup.count('id="career-context-data"'), 1)
        self.assertEqual(markup.count('id="career-context-fallback"'), 1)
        self.assertNotIn("Old fallback", markup)


class NotebookReleaseTests(unittest.TestCase):
    def test_shipped_example_is_reproducible(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "notebook.html"
            notebook.render(ROOT / "examples/career-context.json", output,
                            quarters=ROOT / "examples/notebook-quarters.json")
            self.assertEqual(output.read_bytes(), (ROOT / "CAREER-NOTEBOOK.html").read_bytes())

    @unittest.skipUnless(shutil.which("node"), "Node.js is an optional development check")
    def test_shipped_route_menu_and_source_handlers(self):
        result = subprocess.run([shutil.which("node"), str(ROOT / "tests/check_notebook.cjs")],
                                cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
