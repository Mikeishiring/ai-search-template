"""Automatic preparation, source fidelity and portable-file guarantees."""
import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/career-context-sheet/scripts/render_interview.py"
spec = importlib.util.spec_from_file_location("interview_renderer", SCRIPT)
interview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(interview)
sys.path.insert(0, str(ROOT))
from tools import build_skill


class InterviewTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads((ROOT / "examples/career-context.json").read_text(encoding="utf-8"))
        self.projection = json.loads((ROOT / "examples/interview-preparation.json").read_text(encoding="utf-8"))
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.source = self.folder / "context.json"
        self.draft = self.folder / "preparation.json"
        self.output = self.folder / "interview.html"
        self.save()

    def save(self):
        self.source.write_text(json.dumps(self.packet), encoding="utf-8")
        self.projection["contextSha256"] = interview.fingerprint(self.source)
        self.draft.write_text(json.dumps(self.projection), encoding="utf-8")

    def command(self, *options, source=None, output=None, script=SCRIPT):
        return subprocess.run(
            [sys.executable, "-I", str(script), str(source or self.source), str(self.draft),
             str(output or self.output), *options], cwd=self.folder, capture_output=True, text=True, timeout=20,
        )

    def seed(self, path=None):
        raw = (path or self.output).read_text(encoding="utf-8")
        return json.loads(re.search(r'<script type="application/json" id="interview-preparation-data">(.*?)</script>', raw, re.S)[1])

    def render(self):
        return interview.render(self.source, self.draft, self.output)

    def test_model_draft_preserves_all_selected_narrative_and_evidence(self):
        self.render()
        state = self.seed()
        self.assertEqual(state["reviewStatus"], "draft")
        self.assertEqual(state["opening"], self.projection["opening"])
        self.assertEqual(state["questions"], self.projection["questions"])
        self.assertEqual(state["modelWorkflow"], interview.WORKFLOW)
        self.assertEqual(state["person"], self.packet["person"])
        for story in state["stories"]:
            account = next(a for a in self.packet["accounts"] if a["id"] == story["id"])
            self.assertEqual(story["account"], account)
            self.assertEqual(story["evidence"], [s for ref in account["sourceRefs"] for s in self.packet["sources"] if s["id"] == ref])
        html = self.output.read_text(encoding="utf-8")
        self.assertNotIn("<form", html)
        self.assertNotIn("localStorage", html)
        self.assertNotIn('data-field=', html)
        for field in ("signal", "stories", "opening", "decode", "chapters", "pace"):
            self.assertIn('id="' + field + '"', html)

    def test_existing_projections_without_short_labels_still_render(self):
        for signal in self.projection["signals"]:
            signal.pop("summary", None)
        for question in self.projection["questions"]:
            question.pop("label", None)
        self.projection["priorityGap"].pop("label", None)
        self.save()
        self.render()
        html = self.output.read_text(encoding="utf-8")
        self.assertIn(self.projection["signals"][0]["reason"], html)
        self.assertIn("One open question", html)
        self.assertEqual(self.seed()["questions"], self.projection["questions"])

    def test_short_labels_are_optional_validated_text(self):
        for key, field in (("signals", "summary"), ("questions", "label"), ("priorityGap", "label")):
            for invalid in ("", None, [], {"unexpected": "value"}):
                projection = copy.deepcopy(self.projection)
                entry = projection[key] if key == "priorityGap" else projection[key][0]
                entry[field] = invalid
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ValueError):
                    interview.prepare(self.packet, projection, interview.fingerprint(self.source))

    def test_inspect_supplies_current_fingerprint_and_context_to_model(self):
        result = subprocess.run([sys.executable, "-I", str(SCRIPT), str(self.source), "--inspect"],
                                cwd=self.folder, capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        inspected = json.loads(result.stdout)
        self.assertEqual(inspected["context"], self.packet)
        self.assertEqual(inspected["contextSha256"], interview.fingerprint(self.source))

    def test_correction_requires_new_preparation_and_never_replaces_output(self):
        self.packet["accounts"][0]["contribution"] += " A corrected contribution."
        self.source.write_text(json.dumps(self.packet), encoding="utf-8")
        self.output.write_text("Existing preparation", encoding="utf-8")
        result = self.command("--force")
        self.assertEqual(result.returncode, 2)
        self.assertIn("context changed", result.stderr)
        self.assertEqual(self.output.read_text(), "Existing preparation")

    def test_unknown_duplicate_and_missing_references_are_rejected(self):
        cases = [
            lambda p: p["stories"][0].update(id="missing"),
            lambda p: p["stories"].append(copy.deepcopy(p["stories"][0])),
            lambda p: p["signals"][0].update(storyId="missing"),
            lambda p: p["signals"].append(copy.deepcopy(p["signals"][0])),
            lambda p: p["questions"][0].update(storyId="missing"),
            lambda p: p["questions"][0].update(id="x/<script>"),
            lambda p: p["questions"].append(copy.deepcopy(p["questions"][0])),
            lambda p: p["priorityGap"].update(storyId="missing"),
            lambda p: p["stories"][0].update(account={"contribution": "Invented override"}),
            lambda p: p.update(stories=[]),
            lambda p: p.update(questions=[]),
            lambda p: p.update(opening=[""]),
            lambda p: p["stories"][0].update(timeline=[]),
            lambda p: p["stories"][0].update(chapters=[]),
        ]
        for mutate in cases:
            projection = copy.deepcopy(self.projection)
            mutate(projection)
            with self.subTest(mutation=cases.index(mutate)), self.assertRaises(ValueError):
                interview.prepare(self.packet, projection, interview.fingerprint(self.source))

    def test_no_gap_is_valid_and_does_not_invent_a_question(self):
        self.projection["priorityGap"] = None
        self.save()
        self.render()
        self.assertIsNone(self.seed()["priorityGap"])
        self.assertNotIn("One detail still needed", self.output.read_text(encoding="utf-8"))

    def test_reviewed_context_does_not_mark_generated_answers_reviewed(self):
        self.packet["reviewStatus"] = "person_reviewed"
        self.save()
        self.render()
        self.assertEqual(self.seed()["reviewStatus"], "draft")
        self.assertEqual(self.seed()["contextReviewStatus"], "person_reviewed")

    def test_extracted_bundle_runs_in_isolated_python_without_repository(self):
        bundle = self.folder / "skill.zip"
        build_skill.build(bundle)
        extracted = self.folder / "unrelated location"
        with zipfile.ZipFile(bundle) as archive:
            archive.extractall(extracted)
        script = extracted / build_skill.PREFIX / "scripts/render_interview.py"
        result = self.command(script=script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.seed()["stories"][0]["account"], self.packet["accounts"][0])

    def test_existing_html_context_is_supported_without_mutation(self):
        html = self.folder / "source-context.html"
        interview.render_context.render(self.source, html)
        before = html.read_bytes()
        self.projection["contextSha256"] = interview.fingerprint(html)
        self.draft.write_text(json.dumps(self.projection), encoding="utf-8")
        result = self.command(source=html)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.seed()["stories"][0]["account"], self.packet["accounts"][0])
        self.assertEqual(html.read_bytes(), before)

    def test_optional_synthetic_flag_defaults_to_real(self):
        del self.packet["synthetic"]
        self.save()
        self.render()
        self.assertFalse(self.seed()["synthetic"])
        self.assertNotIn('id="synthetic-note"', self.output.read_text(encoding="utf-8"))

    def test_inert_markup_and_placeholder_text_survive_exactly(self):
        payload = '</script><script>window.INJECTED=true</script>& __DATA__ __OPENING__'
        self.packet["accounts"][0]["title"] = payload
        self.packet["sources"][0]["locator"] = "javascript:alert(1)"
        self.projection["opening"][0] = payload
        self.save()
        self.render()
        self.assertEqual(self.seed()["stories"][0]["title"], payload)
        self.assertEqual(self.seed()["opening"][0], payload)
        html = self.output.read_text(encoding="utf-8")
        self.assertNotIn(payload, html)
        self.assertNotIn('href="javascript:', html)
        self.assertEqual(len(re.findall(r"<script\b", html)), 2)

    def test_local_artifacts_are_not_read_or_copied(self):
        self.packet["accounts"][0]["artifacts"] = [
            {"id": "picture", "title": "Private image", "caption": "Keep in context",
             "file": "missing-sensitive-file.png"}
        ]
        self.save()
        self.render()
        self.assertNotIn("artifacts", self.seed()["stories"][0]["account"])
        self.assertNotIn("missing-sensitive-file", self.output.read_text(encoding="utf-8"))

    def test_existing_output_requires_force_and_force_is_deterministic(self):
        self.output.write_text("Keep these notes", encoding="utf-8")
        self.assertEqual(self.command().returncode, 2)
        self.assertEqual(self.output.read_text(), "Keep these notes")
        self.assertEqual(self.command("--force").returncode, 0)
        first = self.output.read_bytes()
        self.assertEqual(self.command("--force").returncode, 0)
        self.assertEqual(self.output.read_bytes(), first)

    def test_invalid_projection_never_replaces_existing_output(self):
        self.draft.write_text('{"schema":"wrong"}', encoding="utf-8")
        self.output.write_text("Keep these notes", encoding="utf-8")
        result = self.command("--force")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(self.output.read_text(), "Keep these notes")

    def test_cli_preserves_context_even_with_force(self):
        html = self.folder / "context.html"
        interview.render_context.render(self.source, html)
        self.projection["contextSha256"] = interview.fingerprint(html)
        self.draft.write_text(json.dumps(self.projection), encoding="utf-8")
        before = html.read_bytes()
        result = self.command("--force", source=html, output=html)
        self.assertEqual(result.returncode, 2)
        self.assertIn("separate output", result.stderr)
        self.assertEqual(html.read_bytes(), before)

    def test_cli_refuses_outputs_inside_installed_skill(self):
        result = self.command(output=SCRIPT.parent / "personal-output.html")
        self.assertEqual(result.returncode, 2)
        self.assertIn("outside the installed skill", result.stderr)

    def test_atomic_creation_preserves_a_concurrent_writer(self):
        original_link = interview.os.link
        def competing_writer(temporary, destination):
            self.output.write_text("Concurrent notes", encoding="utf-8")
            return original_link(temporary, destination)
        with patch.object(interview.os, "link", side_effect=competing_writer):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                interview.main([str(self.source), str(self.draft), str(self.output)])
        self.assertEqual(self.output.read_text(), "Concurrent notes")
        self.assertEqual(list(self.folder.glob(".career-interview-*.tmp")), [])

    def test_symlink_output_is_refused(self):
        with patch.object(Path, "is_symlink", return_value=True):
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                self.render()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
