"""Installed CLI discovery must support the active desktop installation."""
from pathlib import Path
import unittest
from unittest.mock import patch
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "ai-search-mvp"))
import model_backend
sys.path.insert(0, str(ROOT))
from tools.run_research_demo import audit_events


class LauncherTests(unittest.TestCase):
    def test_active_path_installation_takes_precedence(self):
        with patch.object(model_backend.shutil, "which", return_value="/installed/codex"):
            self.assertEqual(model_backend.executable(), Path("/installed/codex"))

    def test_runtime_diagnostics_are_retained_without_becoming_source_calls(self):
        warning = {"type": "error", "message": "Unrecognized configuration setting."}
        allowed = {"type": "mcp_tool_call", "server": "synthetic_research"}
        shell = {"type": "command_execution"}
        other = {"type": "mcp_tool_call", "server": "other"}
        calls, unexpected, diagnostics = audit_events([warning, allowed, shell, other, {"type": "agent_message"}])
        self.assertEqual(calls, [allowed, shell, other])
        self.assertEqual(unexpected, [shell, other])
        self.assertEqual(diagnostics, [warning["message"]])

    def test_missing_cli_has_an_actionable_error(self):
        with patch.object(model_backend.shutil, "which", return_value=None):
            with patch.object(Path, "glob", return_value=[]):
                with self.assertRaisesRegex(RuntimeError, "put its executable on PATH"):
                    model_backend.executable()


if __name__ == "__main__":
    unittest.main()
