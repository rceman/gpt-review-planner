from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ExecutionModeTests(unittest.TestCase):
    def setup_project(self, mode: str | None):
        temp = tempfile.TemporaryDirectory()
        project = Path(temp.name)
        command = ["bash", str(ROOT / "setup.sh"), "--project", str(project), "--version", "v2.0.0", "--commit", "a" * 40, "--execution-mode", mode] if mode else ["bash", str(ROOT / "setup.sh"), "--project", str(project), "--version", "v2.0.0", "--commit", "a" * 40]
        result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return temp, project, result

    def test_mode_is_required(self):
        temp, project, result = self.setup_project(None)
        self.addCleanup(temp.cleanup)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((project / ".gpt-workflow.lock").exists())

    def test_each_mode_is_persisted_without_inference(self):
        for mode in ("gpt_tunnel_managed", "repository_evidence"):
            temp, project, result = self.setup_project(mode)
            self.addCleanup(temp.cleanup)
            self.assertEqual(result.returncode, 0, result.stderr)
            lock = json.loads((project / ".gpt-workflow.lock").read_text(encoding="utf-8"))
            self.assertEqual(lock["execution_mode"], mode)
            self.assertIn(f"Execution mode: `{mode}`", (project / "AGENTS.md").read_text(encoding="utf-8"))

    def test_update_requires_explicit_mode(self):
        temp, project, result = self.setup_project("repository_evidence")
        self.addCleanup(temp.cleanup)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = subprocess.run(["bash", str(ROOT / "update.sh"), "--project", str(project), "--version", "v2.0.0"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
