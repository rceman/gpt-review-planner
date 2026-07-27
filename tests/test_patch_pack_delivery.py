import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts/validate-patch-pack-delivery.py"


class PatchPackDeliveryTests(unittest.TestCase):
    def fixture(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name) / "pack"
        planner = Path(temp.name) / "planner"
        (root / "scripts").mkdir(parents=True)
        (planner / "scripts").mkdir(parents=True)
        manifest = {"schema_version": 2, "patch_id": "patch-20260727-051338-review-closure"}
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        archive = "patch-20260727-051338-review-closure.tar.gz"
        (root / "AGENT_PROMPT.md").write_text(
            f"Apply patch pack `{archive}` from the Downloads folder.\n", encoding="utf-8"
        )
        for name in ("patch_pack_scope.py", "verify-agent-evidence.py"):
            shutil.copy2(ROOT / "scripts" / name, planner / "scripts" / name)
            shutil.copy2(ROOT / "scripts" / name, root / "scripts" / name)
        return temp, root, planner, archive, archive + ".sha256"

    def run_validator(self, root, planner, archive, sidecar, response=None):
        command = [sys.executable, str(VALIDATOR), "--pack-root", str(root), "--planner-root", str(planner),
                   "--archive-name", archive, "--sidecar-name", sidecar]
        if response:
            command += ["--response-file", str(response)]
        return subprocess.run(command, capture_output=True, text=True)

    def test_representative_fixture_and_response_pass(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            response = root / "response.txt"
            response.write_text(f"PATCH_PACK_NAME\n{archive}\n\nSHA256_FILE_NAME\n{sidecar}\n\n## AGENT_HANDOFF\n\nApply patch pack `{archive}` from the Downloads folder.\n", encoding="utf-8")
            result = self.run_validator(root, planner, archive, sidecar, response)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_name_prompt_and_response_contracts_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            self.assertNotEqual(self.run_validator(root, planner, "wrong.tar.gz", sidecar).returncode, 0)
            (root / "AGENT_PROMPT.md").write_text("missing sentence", encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)
            (root / "AGENT_PROMPT.md").write_text(f"Apply patch pack `{archive}` from the Downloads folder.", encoding="utf-8")
            response = root / "response.txt"
            response.write_text(f"PATCH_PACK_NAME\n{archive}\n\nSHA256_FILE_NAME\n{sidecar}\n\n## AGENT_HANDOFF\n\nApply patch pack `{archive}` from the Downloads folder.\ntrailing\n", encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar, response).returncode, 0)

    def test_tools_must_be_exact_and_start(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            (root / "scripts/patch_pack_scope.py").write_text("#!/usr/bin/env python3\nprint('wrapper')\n", encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)
            shutil.copy2(planner / "scripts/patch_pack_scope.py", root / "scripts/patch_pack_scope.py")
            broken = planner / "scripts/patch_pack_scope.py"
            broken.write_text("raise NameError('broken wrapper')\n", encoding="utf-8")
            shutil.copy2(broken, root / "scripts/patch_pack_scope.py")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)

    def test_documentation_exposes_contract(self):
        handoff = (ROOT / "docs/PATCH_PACK_HANDOFF.md").read_text(encoding="utf-8")
        prompt = (ROOT / "prompts/GPT_CREATE_PATCH_PACK.md").read_text(encoding="utf-8")
        self.assertIn("Prompt-only mode", handoff)
        self.assertIn("No-action mode", handoff)
        self.assertIn("AGENT_HANDOFF", handoff)
        self.assertIn("validate-patch-pack-delivery.py", prompt)
        self.assertIn("byte-identical", prompt)


if __name__ == "__main__":
    unittest.main()
