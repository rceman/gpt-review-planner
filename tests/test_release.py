from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/release.py"


def load_module():
    spec = importlib.util.spec_from_file_location("release_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.strip()


class ReleaseScriptTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def make_repo(self) -> Path:
        temp = Path(tempfile.mkdtemp())
        git(temp, "init", "-q")
        git(temp, "config", "user.name", "Test")
        git(temp, "config", "user.email", "test@example.com")
        (temp / "VERSION").write_text("1.2.3\n", encoding="utf-8")
        (temp / "README.md").write_text("Use immutable vX.Y.Z tags.\n", encoding="utf-8")
        (temp / "CHANGELOG.md").write_text("# Changelog\n\n## Unreleased\n\n- Added a feature.\n\n## 1.2.3 — 2026-01-01\n\n- Previous.\n", encoding="utf-8")
        (temp / "package.json").write_text(json.dumps({"name": "x", "version": "1.2.3"}, indent=2) + "\n", encoding="utf-8")
        (temp / "composer.json").write_text(json.dumps({"name": "x/y", "version": "1.2.3"}, indent=2) + "\n", encoding="utf-8")
        (temp / "Cargo.toml").write_text('[workspace.package]\nversion = "1.2.3"\nedition = "2024"\n', encoding="utf-8")
        config = {
            "schema_version": 1,
            "canonical_version_file": "VERSION",
            "tag_prefix": "v",
            "release_commit_message": "chore(release): v{version}",
            "version_files": [
                {"path": "VERSION", "kind": "plain"},
                {"path": "package.json", "kind": "json", "pointer": "/version"},
                {"path": "composer.json", "kind": "json", "pointer": "/version"},
                {"path": "Cargo.toml", "kind": "toml", "table": "workspace.package", "key": "version"},
            ],
            "forbidden_version_patterns": [
                {"path": "README.md", "regex": r"(?<![A-Za-z0-9])v?\d+\.\d+\.\d+(?![A-Za-z0-9])"}
            ],
            "changelog": {
                "path": "CHANGELOG.md",
                "unreleased_heading": "## Unreleased",
                "release_heading": "## {version} — {date}"
            },
        }
        (temp / "release-config.json").write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
        git(temp, "add", ".")
        git(temp, "commit", "-qm", "base")
        return temp

    def test_prepare_updates_plain_json_and_toml_files(self) -> None:
        repo = self.make_repo()
        config = self.module.load_config(repo, "release-config.json")
        self.module.command_prepare(repo, config, "1.3.0")
        self.assertEqual((repo / "VERSION").read_text().strip(), "1.3.0")
        self.assertEqual(json.loads((repo / "package.json").read_text())["version"], "1.3.0")
        self.assertEqual(json.loads((repo / "composer.json").read_text())["version"], "1.3.0")
        self.assertIn('version = "1.3.0"', (repo / "Cargo.toml").read_text())
        expected_heading = f"## 1.3.0 — {datetime.now(timezone.utc).date().isoformat()}"
        changelog = (repo / "CHANGELOG.md").read_text()
        self.assertIn("## Unreleased", changelog)
        self.assertIn(expected_heading, changelog)
        self.assertLess(changelog.index("## Unreleased"), changelog.index(expected_heading))

    def test_check_rejects_readme_version_literal(self) -> None:
        repo = self.make_repo()
        (repo / "README.md").write_text("Current version: 1.2.3\n", encoding="utf-8")
        config = self.module.load_config(repo, "release-config.json")
        with self.assertRaises(self.module.ReleaseError):
            self.module.command_check(repo, config)

    def test_commit_rejects_unrelated_changes(self) -> None:
        repo = self.make_repo()
        config = self.module.load_config(repo, "release-config.json")
        self.module.command_prepare(repo, config, "1.3.0")
        (repo / "unrelated.txt").write_text("x\n", encoding="utf-8")
        with self.assertRaises(self.module.ReleaseError):
            self.module.command_commit(repo, config)

    def test_commit_and_tag_use_canonical_version(self) -> None:
        repo = self.make_repo()
        config = self.module.load_config(repo, "release-config.json")
        self.module.command_prepare(repo, config, "1.3.0")
        self.module.command_commit(repo, config)
        self.assertEqual(git(repo, "log", "-1", "--pretty=%s"), "chore(release): v1.3.0")
        self.module.command_tag(repo, config)
        self.assertEqual(git(repo, "tag", "--list", "v1.3.0"), "v1.3.0")
        self.module.command_verify_tag(repo, config, "v1.3.0")

    def test_optional_missing_version_file_is_ignored(self) -> None:
        repo = self.make_repo()
        config_path = repo / "release-config.json"
        config = json.loads(config_path.read_text())
        config["version_files"].append({"path": "missing.json", "kind": "json", "pointer": "/version", "optional": True})
        config_path.write_text(json.dumps(config, indent=2) + "\n")
        git(repo, "add", "release-config.json")
        git(repo, "commit", "-qm", "config")
        self.module.command_check(repo, self.module.load_config(repo, "release-config.json"))


if __name__ == "__main__":
    unittest.main()
