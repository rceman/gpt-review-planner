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
        shutil.copytree(ROOT / "examples/gateway-compatible-patch-pack", root)
        (planner / "scripts").mkdir(parents=True)
        for name in ("validate-patch-pack.py", "patch_pack_scope.py", "verify-agent-evidence.py", "verify-agent-result.sh"):
            shutil.copy2(ROOT / "scripts" / name, planner / "scripts" / name)
        (planner / "VERSION").write_bytes((ROOT / "VERSION").read_bytes())
        archive = "patch-20260728-120000-gateway-compatible.tar.gz"
        return temp, root, planner, archive, archive + ".sha256"

    def run_validator(self, root, planner, archive, sidecar, response=None):
        command = [sys.executable, str(VALIDATOR), "--pack-root", str(root), "--planner-root", str(planner),
                   "--archive-name", archive, "--sidecar-name", sidecar]
        if response:
            command += ["--response-file", str(response)]
        return subprocess.run(command, capture_output=True, text=True)

    def response(self, archive, sidecar, *, archive_value=None, sidecar_value=None, handoff_archive=None, suffix=""):
        archive_value = archive if archive_value is None else archive_value
        sidecar_value = sidecar if sidecar_value is None else sidecar_value
        handoff_archive = archive if handoff_archive is None else handoff_archive
        return (f"PATCH_PACK_NAME\n{archive_value}\n\nSHA256_FILE_NAME\n{sidecar_value}\n\n"
                f"## AGENT_HANDOFF\n\nApply patch pack `{handoff_archive}` from the Downloads folder.{suffix}")

    def run_response(self, root, planner, archive, sidecar, text, *, crlf=False):
        response = root / "response.txt"
        if crlf:
            text = text.replace("\n", "\r\n")
        response.write_text(text, encoding="utf-8", newline="")
        return self.run_validator(root, planner, archive, sidecar, response)

    def test_valid_canonical_response_passes(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            result = self.run_response(root, planner, archive, sidecar, self.response(archive, sidecar), crlf=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_cli_archive_and_sidecar_mismatches_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            self.assertNotEqual(self.run_validator(root, planner, "wrong.tar.gz", sidecar).returncode, 0)
            self.assertNotEqual(self.run_validator(root, planner, archive, "wrong.sha256").returncode, 0)

    def test_missing_or_wrong_field_values_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            cases = [
                self.response(archive, sidecar).replace("PATCH_PACK_NAME\n" + archive + "\n", ""),
                self.response(archive, sidecar).replace("SHA256_FILE_NAME\n" + sidecar + "\n", ""),
                self.response(archive, sidecar, archive_value="wrong.tar.gz"),
                self.response(archive, sidecar, sidecar_value="wrong.sha256").replace(
                    "## AGENT_HANDOFF", f"correct sidecar elsewhere: {sidecar}\n\n## AGENT_HANDOFF"
                ),
            ]
            for text in cases:
                self.assertNotEqual(self.run_response(root, planner, archive, sidecar, text).returncode, 0)

    def test_duplicate_markers_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            self.assertNotEqual(self.run_response(root, planner, archive, sidecar, self.response(archive, sidecar).replace("\n\nSHA256", f"\nPATCH_PACK_NAME\n{archive}\n\nSHA256", 1)).returncode, 0)
            self.assertNotEqual(self.run_response(root, planner, archive, sidecar, self.response(archive, sidecar).replace("\n\n## AGENT", f"\nSHA256_FILE_NAME\n{sidecar}\n\n## AGENT", 1)).returncode, 0)

    def test_wrong_handoff_and_trailing_prose_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            self.assertNotEqual(self.run_response(root, planner, archive, sidecar, self.response(archive, sidecar, handoff_archive="wrong.tar.gz")).returncode, 0)
            self.assertNotEqual(self.run_response(root, planner, archive, sidecar, self.response(archive, sidecar, suffix="\ntrailing prose")).returncode, 0)

    def test_missing_prompt_sentence_fails(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            (root / "AGENT_PROMPT.md").write_text("missing sentence", encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)

    def test_missing_tools_and_differences_fail(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            (root / "scripts/patch_pack_scope.py").unlink()
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)
            shutil.copy2(planner / "scripts/patch_pack_scope.py", root / "scripts/patch_pack_scope.py")
            (root / "scripts/verify-agent-evidence.py").unlink()
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)
            shutil.copy2(planner / "scripts/verify-agent-evidence.py", root / "scripts/verify-agent-evidence.py")
            (root / "scripts/patch_pack_scope.py").write_text((root / "scripts/patch_pack_scope.py").read_text() + "\n", encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)

    def test_wrapper_and_top_level_name_error_fail_startup(self):
        temp, root, planner, archive, sidecar = self.fixture()
        with temp:
            wrapper = "#!/usr/bin/env python3\nprint('proxy')\n"
            (root / "scripts/patch_pack_scope.py").write_text(wrapper, encoding="utf-8")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)
            broken = planner / "scripts/patch_pack_scope.py"
            broken.write_text("raise NameError('broken wrapper')\n", encoding="utf-8")
            shutil.copy2(broken, root / "scripts/patch_pack_scope.py")
            self.assertNotEqual(self.run_validator(root, planner, archive, sidecar).returncode, 0)

    def test_documentation_exposes_contract(self):
        handoff = (ROOT / "docs/PATCH_PACK_HANDOFF.md").read_text(encoding="utf-8")
        prompt = (ROOT / "prompts/GPT_CREATE_PATCH_PACK.md").read_text(encoding="utf-8")
        self.assertIn("Prompt-only mode", handoff)
        self.assertIn("No-action mode", handoff)
        self.assertIn("No agent action is required. Preserve the reported state and wait for the next owner instruction.", handoff)
        for field in ("repository", "local repository", "branch", "exact base", "required actions", "runtime gates", "constraints", "final report"):
            self.assertIn(field, handoff)
        self.assertIn("AGENT_HANDOFF", handoff)
        self.assertIn("validate-patch-pack-delivery.py", prompt)
        self.assertIn("byte-identical", prompt)

    def test_planner_headings_are_not_adjacent_empty_headings(self):
        text = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        empty_pair = "## Committed JSON evidence and release automation\n\n## Patch-pack response handoff"
        self.assertNotIn(empty_pair, text)
        self.assertIn("## Patch-pack response handoff", text)
        self.assertIn("## Committed JSON evidence and release automation", text)


if __name__ == "__main__":
    unittest.main()
