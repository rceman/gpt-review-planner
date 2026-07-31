from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

runner_spec = importlib.util.spec_from_file_location(
    "gpt_patch_pack_runner_v2", ROOT / "scripts/gpt-patch-pack-runner-v2.py"
)
assert runner_spec and runner_spec.loader
runner = importlib.util.module_from_spec(runner_spec)
runner_spec.loader.exec_module(runner)

common_spec = importlib.util.spec_from_file_location(
    "gpt_patch_pack_common", ROOT / "scripts/gpt_patch_pack_common.py"
)
assert common_spec and common_spec.loader
common = importlib.util.module_from_spec(common_spec)
common_spec.loader.exec_module(common)


class PatchPackV2Tests(unittest.TestCase):
    def git(self, repo: Path, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()

    def make_repo(self, root: Path) -> tuple[Path, str, str]:
        repo = root / "repo"
        subprocess.run(["git", "init", "-b", "main", str(repo)], check=True, stdout=subprocess.DEVNULL)
        subprocess.run(["git", "-C", str(repo), "config", "user.name", "v2-test"], check=True)
        subprocess.run(["git", "-C", str(repo), "config", "user.email", "v2-test@example.invalid"], check=True)
        (repo / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, stdout=subprocess.DEVNULL)
        return repo, self.git(repo, "rev-parse", "HEAD"), self.git(repo, "rev-parse", "HEAD^{tree}")

    def manifest(self, base: str, tree: str) -> dict:
        return {
            "schema_version": 2,
            "format": "gpt-patch-pack-v2",
            "patch_id": "patch-20260731-000000-v2-test",
            "title": "v2 test",
            "description": "data-only test pack",
            "created_at": "2026-07-31T00:00:00Z",
            "runner_version": "2.0.0",
            "baseline_release": "v2.0.0",
            "execution_mode": "gpt_tunnel_managed",
            "workflow": {
                "repository": "https://github.com/rceman/gpt-review-planner",
                "version": "v2.0.0",
                "commit": "0" * 40,
                "document": "GPT_REVIEW_PLANNER.md",
            },
            "target": {
                "repository": "owner/repo",
                "accepted_origin_urls": ["git@github.com:owner/repo.git"],
                "branch": "main",
                "base_revision": base,
                "remote": "origin",
                "remote_ref": "refs/remotes/origin/main",
            },
            "payload": {"patch": "payload/changes.patch", "format": "git-binary-full-index"},
            "files_created": [], "files_modified": [], "files_deleted": [],
            "target_tree": tree,
            "requirements": [{"id": "REQ-001", "summary": "Exact tree", "acceptance": ["The tree is exact."]}],
            "gates": [{"id": "GATE-001", "name": "Compile", "kind": "command", "argv": ["python3", "-m", "compileall", "-q", "scripts"], "env": {}, "timeout_seconds": 60, "max_output_bytes": 1048576}],
            "compatibility": dict(common.DEFAULT_COMPATIBILITY),
            "metadata": {"planner_commit": "0" * 40, "gpt_static_checks_performed": ["static"], "gpt_runtime_checks_not_performed": ["runtime is agent-owned"]},
        }

    def archive(self, members: list[tuple[str, bytes, str]]):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w:gz") as tf:
            for name, data, kind in members:
                info = tarfile.TarInfo(name)
                if kind == "file":
                    info.mode = 0o644
                    info.size = len(data)
                    tf.addfile(info, io.BytesIO(data))
                elif kind == "dir":
                    info.type = tarfile.DIRTYPE
                    info.mode = 0o755
                    tf.addfile(info)
                else:
                    info.type = getattr(tarfile, kind)
                    info.linkname = "/tmp/marker"
                    tf.addfile(info)
        return raw.getvalue()

    def canonical_members(self, manifest: dict, task: bytes = b"# AGENT_TASK\n") -> list[tuple[str, bytes, str]]:
        manifest_bytes = (json.dumps(manifest, indent=2) + "\n").encode()
        patch = b""
        sums = "".join([
            f"{hashlib.sha256(manifest_bytes).hexdigest()}  MANIFEST.json\n",
            f"{hashlib.sha256(task).hexdigest()}  AGENT_TASK.md\n",
            f"{hashlib.sha256(patch).hexdigest()}  payload/changes.patch\n",
        ]).encode()
        return [("p", b"", "dir"), ("p/payload", b"", "dir"), ("p/MANIFEST.json", manifest_bytes, "file"), ("p/SHA256SUMS", sums, "file"), ("p/AGENT_TASK.md", task, "file"), ("p/payload/changes.patch", patch, "file")]

    def assert_extract_rejected(self, data: bytes) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "pack.tar.gz"
            path.write_bytes(data)
            with self.assertRaises(runner.PackError):
                runner.extract_archive(path, Path(raw) / "out")

    def test_public_runner_rejects_archive_controlled_executable(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            repo, _, _ = self.make_repo(root)
            data = self.archive(self.canonical_members(self.manifest(self.git(repo, "rev-parse", "HEAD"), self.git(repo, "rev-parse", "HEAD^{tree}"))) + [("p/payload/apply.py", b"__import__('pathlib').Path('/tmp/v2-exploit').touch()", "file")])
            archive = root / "pack.tar.gz"; archive.write_bytes(data)
            result = subprocess.run([sys.executable, str(ROOT / "scripts/gpt-patch-pack-runner-v2.py"), "--archive", str(archive), "--archive-sha256", hashlib.sha256(data).hexdigest(), "--repo", str(repo)], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(Path("/tmp/v2-exploit").exists())

    def test_extra_and_missing_canonical_members_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            repo, base, tree = self.make_repo(Path(raw))
            members = self.canonical_members(self.manifest(base, tree))
            self.assert_extract_rejected(self.archive(members + [("p/extra", b"x", "file")]))
            self.assert_extract_rejected(self.archive([item for item in members if item[0] != "p/AGENT_TASK.md"]))
            self.assert_extract_rejected(self.archive([item for item in members if item[0] != "p/payload/changes.patch"]))

    def test_links_traversal_absolute_and_casefold_collisions_are_rejected(self):
        cases = [
            [("p/link", b"", "SYMTYPE")], [("p/hard", b"", "LNKTYPE")],
            [("../escape", b"x", "file")], [("/absolute", b"x", "file")],
            [("p/AGENT_TASK.md", b"x", "file"), ("p/agent_task.md", b"y", "file")],
        ]
        for extra in cases:
            self.assert_extract_rejected(self.archive(extra))

    def test_checksum_and_utf8_boundaries_are_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); repo, base, tree = self.make_repo(root)
            members = self.canonical_members(self.manifest(base, tree), task=b"\xff")
            data = self.archive(members); archive = root / "bad.tar.gz"; archive.write_bytes(data)
            extracted = runner.extract_archive(archive, root / "out")
            runner.verify_checksums(extracted)
            with self.assertRaisesRegex(ValueError, "UTF-8"):
                runner.validate_manifest(common.load_json(extracted / "MANIFEST.json"), pack_root=extracted)
            (extracted / "SHA256SUMS").write_text("not-a-checksum\n", encoding="utf-8")
            with self.assertRaisesRegex(runner.PackError, "malformed checksum"):
                runner.verify_checksums(extracted)

    def test_verify_only_leaves_repository_unchanged(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); repo, base, tree = self.make_repo(root)
            data = self.archive(self.canonical_members(self.manifest(base, tree)))
            archive = root / "pack.tar.gz"; archive.write_bytes(data)
            before = self.git(repo, "status", "--porcelain=v1", "--untracked-files=all")
            result = subprocess.run([sys.executable, str(ROOT / "scripts/gpt-patch-pack-runner-v2.py"), "--archive", str(archive), "--archive-sha256", hashlib.sha256(data).hexdigest(), "--repo", str(repo)], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(self.git(repo, "rev-parse", "HEAD"), base)
            self.assertEqual(self.git(repo, "status", "--porcelain=v1", "--untracked-files=all"), before)

    def test_shared_validator_rejects_unknown_and_placeholder_gate(self):
        with tempfile.TemporaryDirectory() as raw:
            repo, base, tree = self.make_repo(Path(raw))
            value = self.manifest(base, tree)
            common.validate_manifest(value)
            unknown = dict(value); unknown["unexpected"] = True
            with self.assertRaises(ValueError): common.validate_manifest(unknown)
            bad_gate = json.loads(json.dumps(value)); bad_gate["gates"][0]["argv"] = ["true"]
            with self.assertRaises(ValueError): common.validate_manifest(bad_gate)

    def test_compatibility_declarations_are_strict(self):
        with tempfile.TemporaryDirectory() as raw:
            repo, base, tree = self.make_repo(Path(raw))
            value = self.manifest(base, tree)
            common.validate_manifest(value)
            authorized = json.loads(json.dumps(value))
            authorized["compatibility"] = {
                "scope": "declared-readers",
                "authorized": True,
                "canonical_implementation": "GPT Patch Pack v2",
                "legacy_behavior": "read-only declaration",
                "authorization_source": "owner:task-1",
                "supported_legacy_versions": ["v1"],
                "direction": "forward",
                "removal_condition": "permanent",
            }
            common.validate_manifest(authorized)
            incomplete = json.loads(json.dumps(authorized))
            incomplete["compatibility"]["removal_condition"] = None
            with self.assertRaises(ValueError): common.validate_manifest(incomplete)
            unauthorized = json.loads(json.dumps(value))
            unauthorized["compatibility"]["supported_legacy_versions"] = ["v1"]
            with self.assertRaises(ValueError): common.validate_manifest(unauthorized)

    def test_schema_is_strict_and_matches_current_contract_shape(self):
        schema = json.loads((ROOT / "schemas/gpt-patch-pack-v2.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("execution_mode", schema["required"])
        self.assertEqual(schema["properties"]["format"]["const"], "gpt-patch-pack-v2")
        self.assertEqual(schema["properties"]["runner_version"]["const"], "2.0.0")
        self.assertFalse(schema["$defs"]["workflow"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["target"]["additionalProperties"])
        self.assertFalse(schema["$defs"]["gate"]["additionalProperties"])

    def test_v2_selftest_is_deterministic_and_data_only(self):
        result = subprocess.run([sys.executable, str(ROOT / "scripts/selftest-gpt-patch-pack-v2.py")], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GPT_PATCH_PACK_V2_SELFTEST_OK", result.stdout)


if __name__ == "__main__":
    unittest.main()
