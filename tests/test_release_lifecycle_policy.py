from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / "scripts/release.py"
LIFECYCLE_VALIDATOR = ROOT / "scripts/validate-release-lifecycle-task.py"
CONFORMANCE = ROOT / "scripts/validate-release-tool-conformance.py"


def load_release():
    spec = importlib.util.spec_from_file_location("release_lifecycle", RELEASE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.strip()


class ReleaseLifecyclePolicyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.release = load_release()

    def make_repo(self, version: str = "2.1.0", notes: str = "- Runtime policy work.\n") -> Path:
        root = Path(tempfile.mkdtemp())
        git(root, "init", "-q")
        git(root, "config", "user.name", "Lifecycle Test")
        git(root, "config", "user.email", "lifecycle@example.com")
        (root / "VERSION").write_text(version + "\n", encoding="utf-8")
        (root / "README.md").write_text("Use immutable tags.\n", encoding="utf-8")
        (root / "CHANGELOG.md").write_text(
            "# Changelog\n\n## Unreleased\n\n" + notes + "\n## 2.0.0 — 2026-07-31\n\n- Prior.\n",
            encoding="utf-8",
        )
        config = {
            "schema_version": 1,
            "canonical_version_file": "VERSION",
            "tag_prefix": "v",
            "release_commit_message": "chore(release): v{version}",
            "version_files": [{"path": "VERSION", "kind": "plain"}],
            "forbidden_version_patterns": [],
            "changelog": {
                "path": "CHANGELOG.md",
                "unreleased_heading": "## Unreleased",
                "release_heading": "## {version} — {date}",
            },
        }
        (root / "release-config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        git(root, "add", ".")
        git(root, "commit", "-qm", "base")
        return root

    def config(self, repo: Path) -> dict:
        return self.release.load_config(repo, "release-config.json")

    def test_source_state_is_distinct_from_release_ready(self) -> None:
        repo = self.make_repo()
        config = self.config(repo)
        self.release.command_check_source(repo, config)
        with self.assertRaises(self.release.ReleaseError):
            self.release.command_release_ready(repo, config)

    def test_prepare_lower_version_and_pre_set_target(self) -> None:
        repo = self.make_repo("2.1.0")
        config = self.config(repo)
        self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        self.assertEqual((repo / "VERSION").read_text(), "2.2.0\n")
        self.assertIn("## 2.2.0 — 2026-08-03", (repo / "CHANGELOG.md").read_text())
        self.release.command_release_ready(repo, config)

        preset = self.make_repo("2.2.0")
        preset_config = self.config(preset)
        before = (preset / "VERSION").read_bytes()
        self.release.command_prepare(preset, preset_config, "2.2.0", "2026-08-03")
        self.assertEqual((preset / "VERSION").read_bytes(), before)
        self.assertEqual(git(preset, "status", "--porcelain"), "M CHANGELOG.md")
        self.release.command_commit(preset, preset_config)
        self.assertEqual(git(preset, "show", "-s", "--format=%s"), "chore(release): v2.2.0")

    def test_prepare_rejects_downgrade_and_repeated_promotion(self) -> None:
        repo = self.make_repo("2.2.0")
        config = self.config(repo)
        with self.assertRaisesRegex(self.release.ReleaseError, "downgrade"):
            self.release.command_prepare(repo, config, "2.1.9", "2026-08-03")
        self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        before = {path: (repo / path).read_bytes() for path in ("VERSION", "CHANGELOG.md")}
        with self.assertRaises(self.release.ReleaseError):
            self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        self.assertEqual(before, {path: (repo / path).read_bytes() for path in before})

    def test_prepare_rejects_empty_malformed_multiple_and_existing_target(self) -> None:
        for changelog in (
            "# Changelog\n\n## Unreleased\n\n## 2.0.0 — 2026-07-31\n",
            "# Changelog\n\n## Unreleased\n\n- note\n\n## Unreleased\n\n- duplicate\n",
            "# Changelog\n\n##Unreleased\n\n- malformed\n",
            "# Changelog\n\n## Unreleased\n\n- note\n\n## 2.2.0 — 2026-08-02\n",
        ):
            repo = self.make_repo("2.1.0")
            (repo / "CHANGELOG.md").write_text(changelog, encoding="utf-8")
            config = self.config(repo)
            before = (repo / "VERSION").read_bytes()
            with self.assertRaises(self.release.ReleaseError):
                self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
            self.assertEqual((repo / "VERSION").read_bytes(), before)

    def test_prepare_application_failure_restores_all_original_bytes(self) -> None:
        repo = self.make_repo("2.1.0")
        config = self.config(repo)
        before = {path: (repo / path).read_bytes() for path in ("VERSION", "CHANGELOG.md")}
        original_replace = os.replace
        calls = 0

        def failing_replace(source, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("injected replace failure")
            return original_replace(source, target)

        with mock.patch.object(self.release.os, "replace", side_effect=failing_replace):
            with self.assertRaises(self.release.ReleaseError):
                self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        self.assertEqual(before, {path: (repo / path).read_bytes() for path in before})
        self.assertEqual(git(repo, "status", "--porcelain"), "")

    def test_release_commit_accepts_changelog_only_and_rejects_unrelated_or_empty(self) -> None:
        repo = self.make_repo("2.2.0")
        config = self.config(repo)
        self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        self.release.command_commit(repo, config)
        with self.assertRaisesRegex(self.release.ReleaseError, "empty"):
            self.release.command_commit(repo, config)

        unrelated = self.make_repo("2.2.0")
        unrelated_config = self.config(unrelated)
        self.release.command_prepare(unrelated, unrelated_config, "2.2.0", "2026-08-03")
        (unrelated / "unrelated.txt").write_text("not a release file\n", encoding="utf-8")
        with self.assertRaises(self.release.ReleaseError):
            self.release.command_commit(unrelated, unrelated_config)

    def test_annotated_tag_identity_and_lightweight_rejection(self) -> None:
        repo = self.make_repo("2.2.0")
        config = self.config(repo)
        self.release.command_prepare(repo, config, "2.2.0", "2026-08-03")
        self.release.command_commit(repo, config)
        self.release.command_tag_ready(repo, config)
        self.release.command_tag(repo, config)
        self.release.command_verify_tag(repo, config, "v2.2.0")

        lightweight = self.make_repo("2.2.0")
        lightweight_config = self.config(lightweight)
        self.release.command_prepare(lightweight, lightweight_config, "2.2.0", "2026-08-03")
        self.release.command_commit(lightweight, lightweight_config)
        git(lightweight, "tag", "v2.2.0")
        with self.assertRaisesRegex(self.release.ReleaseError, "lightweight"):
            self.release.command_verify_tag(lightweight, lightweight_config, "v2.2.0")

    def test_tool_conformance_and_exact_cli_names(self) -> None:
        result = subprocess.run(
            [sys.executable, str(CONFORMANCE), "--release-script", str(RELEASE)],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        help_result = subprocess.run([sys.executable, str(RELEASE), "--help"], text=True, capture_output=True)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn("check-release-ready", help_result.stdout)
        self.assertIn("check-tag-ready", help_result.stdout)

    def test_lifecycle_task_validator_accepts_both_modes_and_rejects_missing_or_contradictory(self) -> None:
        implementation = {
            "constraints": [
                "Release lifecycle mode: implementation_unreleased",
                "Release target version: 2.2.0",
            ],
            "required_gates": ["python3 scripts/release.py check-source"],
        }
        publication = {
            "constraints": [
                "Release lifecycle mode: release_publication",
                "Release target version: 2.2.0",
            ],
            "required_gates": [
                "python3 scripts/release.py prepare 2.2.0",
                "python3 scripts/release.py check-release-ready",
                "python3 scripts/release.py commit",
                "python3 scripts/release.py check-tag-ready",
                "python3 scripts/release.py verify-tag v2.2.0",
            ],
        }
        for data in (implementation, publication):
            path = Path(tempfile.mkdtemp()) / "task.json"
            path.write_text(json.dumps(data), encoding="utf-8")
            result = subprocess.run([sys.executable, str(LIFECYCLE_VALIDATOR), str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
        invalid = {
            "constraints": ["Release lifecycle mode: implementation_unreleased", "Release target version: 2.2.0"],
            "required_gates": ["python3 scripts/release.py prepare 2.2.0"],
        }
        path = Path(tempfile.mkdtemp()) / "task.json"
        path.write_text(json.dumps(invalid), encoding="utf-8")
        result = subprocess.run([sys.executable, str(LIFECYCLE_VALIDATOR), str(path)], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)

    def test_review_closure_uses_attached_project_release_script(self) -> None:
        repo = self.make_repo("2.2.0")
        (repo / "scripts").mkdir()
        shutil.copy2(RELEASE, repo / "scripts" / "release.py")
        task = repo / "task.json"
        task.write_text(
            json.dumps(
                {
                    "constraints": [
                        "Release lifecycle mode: implementation_unreleased",
                        "Release target version: 2.2.0",
                    ],
                    "required_gates": ["python3 scripts/release.py check-source"],
                }
            ),
            encoding="utf-8",
        )
        git(repo, "add", "scripts/release.py", "task.json")
        git(repo, "commit", "-qm", "attach release lifecycle task")
        closure = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts/validate-review-closure.py"),
                "--release-task",
                str(task),
                "--repo",
                str(repo),
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(closure.returncode, 0, closure.stderr)


if __name__ == "__main__":
    unittest.main()
