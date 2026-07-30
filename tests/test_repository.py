from __future__ import annotations

import json
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class RepositoryTest(unittest.TestCase):
    def test_required_v1_files_exist(self) -> None:
        for relative in (
            "GPT_REVIEW_PLANNER.md",
            "README.md",
            "VERSION",
            "setup.sh",
            "update.sh",
            "scripts/gpt-patch-pack-runner-v1.py",
            "scripts/build-gpt-patch-pack-v1.py",
            "scripts/selftest-gpt-patch-pack-v1.py",
            "scripts/validate-patch-pack.py",
            "scripts/verify-agent-evidence.py",
            "schemas/patch-manifest.schema.json",
            "templates/gpt-patch-pack-v1/AGENT_TASK.md",
            "templates/gpt-patch-pack-v1/MANIFEST.example.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_v1_template_manifest_is_valid_json(self) -> None:
        data = json.loads(
            (ROOT / "templates/gpt-patch-pack-v1/MANIFEST.example.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["schema_version"], 2)
        self.assertEqual(data["workflow"]["document"], "GPT_REVIEW_PLANNER.md")

    def test_release_cli_and_runbook_remain_available(self) -> None:
        runbook = (ROOT / "docs/RELEASE_PROCESS.md").read_text(encoding="utf-8")
        prompt = (ROOT / "prompts/AGENT_RELEASE_VERSION.md").read_text(encoding="utf-8")
        help_text = subprocess.run(
            ["python3", str(ROOT / "scripts/release.py"), "--help"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        for command in ("check", "prepare", "commit", "tag", "verify-tag"):
            self.assertIn(command, help_text)
        self.assertIn("Do not create a tag until release-commit CI succeeds", runbook)
        self.assertIn("GitHub Release requires explicit owner authorization", runbook)
        self.assertNotRegex(prompt, r"\b[0-9a-f]{40}\b")

    def test_archive_workflow_contract_remains_present(self) -> None:
        for relative in (
            "docs/PROJECT_ARCHIVE_REVIEW.md",
            "prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md",
            "prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md",
            "prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_gpt_policy_keeps_runtime_ownership_separate(self) -> None:
        workflow = (ROOT / "GPT_REVIEW_PLANNER.md").read_text(encoding="utf-8")
        for section in (
            "GPT_STATIC_CHECKS_PERFORMED",
            "GPT_RUNTIME_CHECKS_NOT_PERFORMED",
            "AGENT_RUNTIME_GATES_REQUIRED",
            "AGENT_RUNTIME_RESULTS",
            "runtime validation not executed by GPT",
        ):
            self.assertIn(section, workflow)


if __name__ == "__main__":
    unittest.main()
