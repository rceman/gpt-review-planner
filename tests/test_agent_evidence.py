from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/verify-agent-evidence.py"


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def git(repo: Path, *args: str) -> str:
    return run("git", "-C", str(repo), *args).stdout.strip()


def snippet_hash(text: bytes, start: int, end: int) -> str:
    return hashlib.sha256(b"".join(text.splitlines(keepends=True)[start - 1 : end])).hexdigest()


class AgentEvidenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.roots: list[Path] = []

    def tearDown(self) -> None:
        for root in self.roots:
            shutil.rmtree(root, ignore_errors=True)

    def make_case(self) -> tuple[Path, Path, str, Path, dict[str, object]]:
        root = Path(tempfile.mkdtemp())
        self.roots.append(root)
        repo = root / "repo"
        pack = root / "pack"
        repo.mkdir()
        pack.mkdir()
        git(repo, "init", "-q")
        git(repo, "config", "user.name", "Test")
        git(repo, "config", "user.email", "test@example.com")
        (repo / "file.txt").write_text("base\n", encoding="utf-8")
        (repo / "delete.txt").write_text("legacy\n", encoding="utf-8")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "base")
        base = git(repo, "rev-parse", "HEAD")

        implementation_text = b"implementation\nproof line\n"
        (repo / "file.txt").write_bytes(implementation_text)
        (repo / "config.json").write_text('{"version_source":"VERSION"}\n', encoding="utf-8")
        (repo / "delete.txt").unlink()
        git(repo, "add", "-A")
        git(repo, "commit", "-qm", "implementation")
        implementation = git(repo, "rev-parse", "HEAD")

        patch_id = "patch-20260724-103354-evidence-checker"
        evidence_rel = Path(".gpt-review/evidence/v1.0.0") / patch_id
        manifest: dict[str, object] = {
            "schema_version": 2,
            "format": "gpt-patch-pack-v1",
            "patch_id": patch_id,
            "title": "Committed evidence checker",
            "description": "Adds compact committed JSON evidence.",
            "created_at": "2026-07-24T10:33:54Z",
            "patch_timestamp": "20260724-103354",
            "patch_slug": "evidence-checker",
            "baseline_release": "v1.0.0",
            "evidence_directory": evidence_rel.as_posix(),
            "workflow": {
                "repository": "https://example.test/workflow",
                "version": "v1.0.1",
                "commit": base,
                "document": "GPT_REVIEW_PLANNER.md",
            },
            "target": {"repository": "owner/repo", "branch": "feature/test", "base_revision": base},
            "files_created": ["config.json"],
            "files_modified": ["file.txt"],
            "files_deleted": ["delete.txt"],
            "requirements": [
                {"id": "R1", "summary": "Implement proof checker", "acceptance": ["Source proof validates"]},
                {"id": "R2", "summary": "Store JSON configuration", "acceptance": ["Pointer matches"]},
                {"id": "R3", "summary": "Delete legacy file", "acceptance": ["File is absent"]},
            ],
            "gates": [
                {"id": "unit", "name": "Unit tests", "kind": "command", "command": "python -m unittest"},
                {"id": "ci", "name": "Validate", "kind": "github-actions", "workflow": "Validate", "head": "implementation"},
                {"id": "scope", "name": "Exact scope", "kind": "scope"},
            ],
            "gpt_static_checks_performed": ["static review"],
            "gpt_runtime_checks_not_performed": ["tests"],
            "known_integration_risks": [],
            "forbidden_deviations": [],
        }
        manifest_raw = json.dumps(manifest, indent=2) + "\n"
        (pack / "manifest.json").write_text(manifest_raw, encoding="utf-8")
        evidence = repo / evidence_rel
        evidence.mkdir(parents=True)
        (evidence / "manifest.json").write_text(manifest_raw, encoding="utf-8")
        report = {
            "schema_version": 1,
            "implementation_commit": implementation,
            "compatibility_scope": "none",
            "compatibility_authorized": False,
            "compatibility_features_added": [],
            "legacy_paths_added": [],
            "fallbacks_added": [],
            "migration_behavior_added": [],
            "requirements": [
                {
                    "id": "R1",
                    "status": "pass",
                    "proofs": [
                        {
                            "kind": "source",
                            "path": "file.txt",
                            "lines": [1, 2],
                            "sha256": snippet_hash(implementation_text, 1, 2),
                            "symbol": "proof line",
                        }
                    ],
                },
                {
                    "id": "R2",
                    "status": "pass",
                    "proofs": [
                        {"kind": "json", "path": "config.json", "pointer": "/version_source", "value": "VERSION"}
                    ],
                },
                {"id": "R3", "status": "pass", "proofs": [{"kind": "deletion", "path": "delete.txt"}]},
            ],
            "gates": [
                {"id": "unit", "status": "pass", "exit": 0, "tests": 3, "summary": "Ran 3 tests ... OK"},
                {"id": "ci", "status": "pass", "run": 123, "job": 456, "url": "https://github.com/o/r/actions/runs/123"},
                {"id": "scope", "status": "pass"},
            ],
            "deviations": [],
        }
        (evidence / "evidence.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        git(repo, "add", evidence_rel.as_posix())
        return repo, pack, implementation, evidence, report

    def verify_prepare(self, repo: Path, pack: Path, implementation: str, *, check: bool = True) -> subprocess.CompletedProcess[str]:
        return run(
            "python3", str(SCRIPT), "prepare", "--pack", str(pack), "--repo", str(repo),
            "--implementation-commit", implementation, check=check,
        )

    def test_prepare_and_committed_modes_accept_two_file_json_evidence(self) -> None:
        repo, pack, implementation, _, _ = self.make_case()
        self.assertIn("PASS", self.verify_prepare(repo, pack, implementation).stdout)
        git(repo, "commit", "-qm", "evidence")
        evidence_commit = git(repo, "rev-parse", "HEAD")
        result = run(
            "python3", str(SCRIPT), "committed", "--pack", str(pack), "--repo", str(repo),
            "--implementation-commit", implementation, "--evidence-commit", evidence_commit,
        )
        self.assertIn("PASS", result.stdout)

    def test_rejects_self_referential_or_redundant_fields(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        report["evidence_commit"] = "0" * 40
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unknown top-level fields", result.stderr)

    def test_rejects_evidence_head_ci_gate(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        manifest = json.loads((pack / "manifest.json").read_text(encoding="utf-8"))
        manifest["gates"][1]["head"] = "evidence"
        manifest_raw = json.dumps(manifest, indent=2) + "\n"
        (pack / "manifest.json").write_text(manifest_raw, encoding="utf-8")
        (evidence / "manifest.json").write_text(manifest_raw, encoding="utf-8")
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "manifest.json").relative_to(repo).as_posix())
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("evidence-head CI is external metadata", result.stderr)

    def test_accepts_implementation_head_ci_gate(self) -> None:
        repo, pack, implementation, _, _ = self.make_case()
        result = self.verify_prepare(repo, pack, implementation)
        self.assertIn("PASS", result.stdout)

    def test_rejects_non_identical_manifest_copy(self) -> None:
        repo, pack, implementation, evidence, _ = self.make_case()
        (evidence / "manifest.json").write_text("{}\n", encoding="utf-8")
        git(repo, "add", (evidence / "manifest.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("byte-identical", result.stderr)

    def test_rejects_bad_line_hash(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        report["requirements"][0]["proofs"][0]["sha256"] = "0" * 64
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("sha256 mismatch", result.stderr)

    def test_rejects_missing_requirement_or_gate(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        report["requirements"].pop()
        report["gates"].pop()
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue("missing IDs" in result.stderr)

    def test_rejects_failed_gate_even_with_deviation(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        report["deviations"] = [{
            "id": "D1", "kind": "test", "summary": "Unit gate failed.",
            "workaround": "No workaround accepted.", "scope_changed": False,
            "behavior_changed": False, "requirements": []
        }]
        report["gates"][0] = {"id": "unit", "status": "fail", "exit": 1, "deviation": "D1"}
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("did not pass", result.stderr)

    def test_accepts_owner_approved_manifest_correction_scope_deviation(self) -> None:
        repo, pack, implementation, _, report = self.make_case()
        report["deviations"] = [{
            "id": "D1",
            "kind": "manifest-correction",
            "summary": "Added a stale test path to the approved manifest scope.",
            "workaround": "Used the amended manifest for exact-scope validation.",
            "scope_changed": True,
            "behavior_changed": False,
            "requirements": ["R2", "R3"],
        }]
        evidence = repo / ".gpt-review/evidence/v1.0.0/patch-20260724-103354-evidence-checker/evidence.json"
        evidence.write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", evidence.relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation)
        self.assertIn("PASS", result.stdout)

    def test_rejects_proof_citing_evidence_directory(self) -> None:
        repo, pack, implementation, evidence, report = self.make_case()
        report["requirements"][0]["proofs"][0]["path"] = (evidence / "evidence.json").relative_to(repo).as_posix()
        (evidence / "evidence.json").write_text(json.dumps(report), encoding="utf-8")
        git(repo, "add", (evidence / "evidence.json").relative_to(repo).as_posix())
        result = self.verify_prepare(repo, pack, implementation, check=False)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must not cite evidence files", result.stderr)


if __name__ == "__main__":
    unittest.main()
