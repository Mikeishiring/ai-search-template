"""Portable distribution and direct skill entrypoint behavior."""
import contextlib
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
sys.path.insert(0, str(ROOT))
from tools import build_skill


class SkillBundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.output = self.directory / "skill.zip"

    def extracted(self):
        build_skill.build(self.output)
        extracted = self.directory / "unrelated folder with spaces"
        with zipfile.ZipFile(self.output) as archive:
            archive.extractall(extracted)
        return extracted / build_skill.PREFIX

    def command(self, skill, source, output, *options):
        # Isolated Python and an unrelated working directory prevent accidental
        # imports from the repository or the developer's Python environment.
        return subprocess.run(
            [sys.executable, "-I", str(skill / "scripts/render_context.py"),
             str(source), str(output), *options],
            cwd=self.directory, text=True, capture_output=True, timeout=20,
        )

    def source(self):
        source = self.directory / "selected.json"
        source.write_bytes((ROOT / "examples/career-context.json").read_bytes())
        return source

    def test_only_declared_resources_and_license_are_packaged(self):
        result = build_skill.build(self.output)
        with zipfile.ZipFile(self.output) as archive:
            expected = {build_skill.PREFIX + "/" + name for name in (*build_skill.MEMBERS, "LICENSE")}
            self.assertEqual(set(archive.namelist()), expected)
            self.assertEqual(len(archive.namelist()), len(expected))
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) for i in archive.infolist()))
        self.assertEqual(result["files"], len(build_skill.MEMBERS) + 1)

    def test_repeated_build_is_identical_and_replacement_is_explicit(self):
        first = build_skill.build(self.output)
        second = build_skill.build(self.directory / "second.zip")
        self.assertEqual(first["sha256"], second["sha256"])
        with self.assertRaises(ValueError):
            build_skill.build(self.output)
        self.assertEqual(first["sha256"], build_skill.build(self.output, force=True)["sha256"])

    def test_unlisted_files_are_excluded_and_line_endings_are_normalized(self):
        source_root = self.directory / "fixture"
        for name in build_skill.MEMBERS:
            target = source_root / build_skill.SKILL / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"selected\r\ntext\r\n")
        (source_root / "LICENSE").write_bytes(b"license\r\n")
        baseline = build_skill.bundle_bytes(source_root)
        (source_root / build_skill.SKILL / "personal-notes.txt").write_text("PRIVATE TEST SENTINEL")
        for path in source_root.rglob("*"):
            if path.is_file():
                path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
        self.assertEqual(baseline, build_skill.bundle_bytes(source_root))
        with zipfile.ZipFile(io.BytesIO(baseline)) as archive:
            self.assertNotIn(b"PRIVATE TEST SENTINEL", b"".join(archive.read(n) for n in archive.namelist()))

    def test_missing_inputs_do_not_replace_existing_bundle(self):
        self.output.write_bytes(b"previous bundle")
        with patch.object(build_skill, "ROOT", self.directory / "missing"):
            with self.assertRaises(ValueError):
                build_skill.build(self.output, force=True)
        self.assertEqual(self.output.read_bytes(), b"previous bundle")

    def test_refuses_bundle_inside_checkout(self):
        with self.assertRaises(ValueError):
            build_skill.build(ROOT / "skill.zip")

    def test_symlink_inputs_are_rejected(self):
        original = Path.is_symlink
        def selected_link(path):
            return path.name == "sheet.html" or original(path)
        with patch.object(Path, "is_symlink", selected_link):
            with self.assertRaisesRegex(ValueError, "symbolic links"):
                build_skill.bundle_bytes(ROOT)

    def test_extracted_skill_renders_and_roundtrips_without_repository(self):
        skill = self.extracted()
        source = self.source()
        output = self.directory / "career.html"
        result = self.command(skill, source, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        packet = re.search(r'<script id="career-context-data" type="application/json">(.*?)</script>',
                           output.read_text(encoding="utf-8"), re.S)
        self.assertEqual(json.loads(packet[1]), json.loads(source.read_text(encoding="utf-8")))
        rebuilt = self.directory / "rebuilt.html"
        result = self.command(skill, output, rebuilt)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(output.read_bytes(), rebuilt.read_bytes())
        for document in skill.rglob("*.md"):
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
                if not re.match(r"^[a-zA-Z]+:|^#", target):
                    self.assertTrue((document.parent / target.split("#")[0]).exists(), target)

    def test_direct_renderer_preserves_output_until_force(self):
        skill = self.extracted()
        source = self.source()
        output = self.directory / "career.html"
        output.write_text("Keep my work", encoding="utf-8")
        result = self.command(skill, source, output)
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(output.read_text(), "Keep my work")
        result = self.command(skill, source, output, "--force")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("career-context-data", output.read_text(encoding="utf-8"))

    def test_extracted_skill_preserves_the_complete_document(self):
        skill = self.extracted()
        source = self.directory / 'complete.json'
        source.write_bytes((ROOT / 'examples/complete-context.json').read_bytes())
        output = self.directory / 'complete.html'
        result = self.command(skill, source, output)
        self.assertEqual(result.returncode, 0, result.stderr)
        markup = output.read_text(encoding='utf-8')
        packet = json.loads(re.search(r'<script id="career-context-data" type="application/json">(.*?)</script>', markup, re.S)[1])
        self.assertEqual(packet, json.loads(source.read_text(encoding='utf-8')))
        for period in packet['timeline']:
            self.assertIn('id="quarter-' + period['id'] + '"', markup)
        for story in packet['interview']['stories']:
            self.assertIn('id="prep-story-' + story['id'] + '"', markup)

    def test_invalid_packet_with_force_does_not_replace_output(self):
        skill = self.extracted()
        source = self.directory / "invalid.json"
        source.write_text('{"schema":"wrong"}')
        output = self.directory / "career.html"
        output.write_text("Keep my work", encoding="utf-8")
        result = self.command(skill, source, output, "--force")
        self.assertEqual(result.returncode, 2)
        self.assertNotIn("Traceback", result.stderr)
        self.assertEqual(output.read_text(), "Keep my work")

    def test_direct_renderer_does_not_replace_a_concurrently_created_file(self):
        skill = self.extracted()
        spec = importlib.util.spec_from_file_location("extracted_renderer", skill / "scripts/render_context.py")
        renderer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(renderer)
        source = self.source()
        output = self.directory / "career.html"
        original_link = renderer.publish_new
        def competing_writer(temporary, destination):
            output.write_text("Concurrent work", encoding="utf-8")
            return original_link(temporary, destination)
        with patch.object(renderer, "publish_new", side_effect=competing_writer):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                renderer.main([str(source), str(output)])
        self.assertEqual(output.read_text(), "Concurrent work")

    def test_direct_renderer_rejects_non_html_destination(self):
        skill = self.extracted()
        source = self.source()
        before = source.read_bytes()
        result = self.command(skill, source, source, "--force")
        self.assertEqual(result.returncode, 2)
        self.assertEqual(source.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
