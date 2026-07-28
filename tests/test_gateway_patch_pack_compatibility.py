from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMANTIC = ROOT / "scripts/validate-patch-pack.py"
DELIVERY = ROOT / "scripts/validate-patch-pack-delivery.py"
FIXTURE = ROOT / "examples/gateway-compatible-patch-pack"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class GatewayPatchPackCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = Path(tempfile.mkdtemp())
        self.pack = self.temp / "pack"
        shutil.copytree(FIXTURE, self.pack)

    def tearDown(self) -> None:
        shutil.rmtree(self.temp, ignore_errors=True)

    def semantic(self, *, json_mode: bool = False) -> subprocess.CompletedProcess[str]:
        args = ["python3", str(SEMANTIC)]
        if json_mode:
            args += ["--format", "json"]
        args.append(str(self.pack))
        return run(*args)

    def result_json(self) -> dict[str, object]:
        result = self.semantic(json_mode=True)
        return json.loads(result.stdout)

    def delivery(self, mode: str, response: str, *, archive: str | None = None, sidecar: str | None = None, json_mode: bool = False, planner: Path | None = None) -> subprocess.CompletedProcess[str]:
        args = ["python3", str(DELIVERY), "--mode", mode]
        if json_mode:
            args += ["--format", "json"]
        if mode in {"manual-download", "gateway-task-bundle"}:
            args += ["--pack-root", str(self.pack), "--planner-root", str(planner or ROOT)]
            args += ["--archive-name", archive or "patch-20260728-120000-gateway-compatible.tar.gz"]
            args += ["--sidecar-name", sidecar or "patch-20260728-120000-gateway-compatible.tar.gz.sha256"]
        args += ["--response-file", str(self.pack / response)]
        return run(*args)

    def test_valid_fixture_passes_text_and_json_modes(self) -> None:
        text = self.semantic()
        self.assertEqual(text.returncode, 0, text.stderr)
        result = self.semantic(json_mode=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["schema_version"], 1)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["validator"], "gpt-review-planner")
        self.assertEqual(payload["patch_id"], "patch-20260728-120000-gateway-compatible")
        self.assertEqual(payload["errors"], [])
        self.assertIsInstance(payload["warnings"], list)
        self.assertEqual(set(payload), {"schema_version", "valid", "validator", "validator_version", "workflow_commit", "patch_id", "errors", "warnings"})

    def test_missing_symlink_empty_oversized_nul_and_invalid_utf8_handoff_fail(self) -> None:
        handoff = self.pack / "AGENT_HANDOFF.md"
        cases = []
        cases.append(("missing_agent_handoff", lambda: handoff.unlink()))
        cases.append(("symlink_required_file", lambda: (handoff.unlink(), handoff.symlink_to("README_FIRST.md"))))
        cases.append(("empty_agent_handoff", lambda: handoff.write_bytes(b"")))
        cases.append(("oversized_agent_handoff", lambda: handoff.write_bytes(b"# AGENT_HANDOFF\n" + b"x" * (129 * 1024))))
        cases.append(("nul_agent_handoff", lambda: handoff.write_bytes(handoff.read_bytes() + b"\0")))
        cases.append(("invalid_agent_handoff_utf8", lambda: handoff.write_bytes(b"\xff\xfe")))
        for code, mutate in cases:
            with self.subTest(code=code):
                shutil.rmtree(self.pack)
                shutil.copytree(FIXTURE, self.pack)
                handoff = self.pack / "AGENT_HANDOFF.md"
                mutate()
                payload = self.result_json()
                self.assertFalse(payload["valid"])
                self.assertIn(code, {item["code"] for item in payload["errors"]})

    def test_missing_heading_and_manifest_identity_mismatches_fail(self) -> None:
        handoff = self.pack / "AGENT_HANDOFF.md"
        handoff.write_text(handoff.read_text(encoding="utf-8").replace("## REPAIR_POLICY", "## REPAIR-POLICY"), encoding="utf-8")
        payload = self.result_json()
        self.assertIn("missing_agent_handoff_heading", {item["code"] for item in payload["errors"]})

        for field, old, new in (
            ("patch", "patch-20260728-120000-gateway-compatible", "patch-20260728-120000-other"),
            ("workflow", "723a8f2a10b9413dadedaf225ad9921eca6b0d4b", "2222222222222222222222222222222222222222"),
            ("evidence", ".gpt-review/evidence/v1.2.0/patch-20260728-120000-gateway-compatible", ".gpt-review/evidence/v1.2.0/patch-20260728-120000-other"),
        ):
            with self.subTest(field=field):
                shutil.rmtree(self.pack)
                shutil.copytree(FIXTURE, self.pack)
                path = self.pack / "AGENT_HANDOFF.md"
                path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")
                codes = {item["code"] for item in self.result_json()["errors"]}
                self.assertIn("handoff_identity_mismatch", codes)

    def test_targeted_placeholder_rules_do_not_reject_shell_comparison_or_xml(self) -> None:
        handoff = self.pack / "AGENT_HANDOFF.md"
        original = handoff.read_text(encoding="utf-8")
        for token in ("REPLACE_VALUE", "REPLACE_WITH_VALUE", "TODO: fill", "TBD: fill", "{{PLACEHOLDER}}", "${REPLACE_VALUE}"):
            with self.subTest(token=token):
                handoff.write_text(original + "\n" + token + "\n", encoding="utf-8")
                self.assertIn("unresolved_placeholder", {item["code"] for item in self.result_json()["errors"]})
        handoff.write_text(original + "\n`2>errors.log`, `1 < 2`, `a >> b`, and `<fixture/>` are valid.\n", encoding="utf-8")
        (self.pack / "AGENT_PROMPT.md").write_bytes(handoff.read_bytes())
        self.assertEqual(self.semantic().returncode, 0, self.semantic().stderr)

    def test_agent_prompt_alias_policy_is_deterministic(self) -> None:
        alias = self.pack / "AGENT_PROMPT.md"
        payload = self.result_json()
        self.assertTrue(payload["valid"])
        self.assertIn("deprecated_agent_prompt_alias", {item["code"] for item in payload["warnings"]})
        alias.write_text(alias.read_text(encoding="utf-8") + "\ndivergence\n", encoding="utf-8")
        self.assertIn("divergent_agent_prompt", {item["code"] for item in self.result_json()["errors"]})
        alias.unlink()
        self.assertEqual(self.semantic().returncode, 0, self.semantic().stderr)

    def test_invalid_json_and_duplicate_keys_have_stable_error_codes(self) -> None:
        manifest = self.pack / "manifest.json"
        manifest.write_text('{"schema_version":2,"schema_version":2}', encoding="utf-8")
        first = self.result_json()
        second = self.result_json()
        self.assertEqual(first["errors"], second["errors"])
        self.assertIn("invalid_json", {item["code"] for item in first["errors"]})

    def test_transport_fields_and_yaml_are_not_planner_manifest_inputs(self) -> None:
        manifest_path = self.pack / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key in ("gateway_id", "project_id", "task_id", "task_execution_mode", "bundle_sha256", "result_path", "airelay_session"):
            with self.subTest(key=key):
                value = json.loads(json.dumps(manifest))
                value[key] = "transport-owned"
                manifest_path.write_text(json.dumps(value), encoding="utf-8")
                self.assertIn("transport_field_in_manifest", {item["code"] for item in self.result_json()["errors"]})
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        (self.pack / "manifest.yaml").write_text("schema_version: 2\n", encoding="utf-8")
        self.assertEqual(self.semantic().returncode, 0, self.semantic().stderr)
        validator = SEMANTIC.read_text(encoding="utf-8")
        self.assertNotIn("import yaml", validator)

    def test_delivery_manual_and_gateway_modes_pass(self) -> None:
        manual = self.delivery("manual-download", "delivery/manual-response.md")
        self.assertEqual(manual.returncode, 0, manual.stderr)
        gateway = self.delivery("gateway-task-bundle", "delivery/gateway-response.md", json_mode=True)
        self.assertEqual(gateway.returncode, 0, gateway.stderr)
        payload = json.loads(gateway.stdout)
        self.assertTrue(payload["valid"])
        self.assertEqual(payload["mode"], "gateway-task-bundle")

    def test_delivery_prompt_only_and_no_action_modes_pass(self) -> None:
        prompt = self.pack / "delivery/prompt-only.md"
        prompt.write_text("## AGENT_HANDOFF\n\nRun the bounded local task.\n", encoding="utf-8")
        no_action = self.pack / "delivery/no-action.md"
        no_action.write_text("## AGENT_HANDOFF\n\nNo agent action is required. Preserve the reported state and wait for the next owner instruction.\n", encoding="utf-8")
        self.assertEqual(self.delivery("prompt-only", "delivery/prompt-only.md").returncode, 0)
        self.assertEqual(self.delivery("no-action", "delivery/no-action.md").returncode, 0)

    def test_delivery_rejects_wrong_names_tool_mismatch_and_startup_failure(self) -> None:
        wrong_archive = self.delivery("manual-download", "delivery/manual-response.md", archive="wrong.tar.gz")
        self.assertIn("wrong_archive_basename", wrong_archive.stderr)
        wrong_sidecar = self.delivery("manual-download", "delivery/manual-response.md", sidecar="wrong.sha256")
        self.assertIn("wrong_sidecar_basename", wrong_sidecar.stderr)
        scope = self.pack / "scripts/patch_pack_scope.py"
        scope.write_text(scope.read_text(encoding="utf-8") + "\n# mismatch\n", encoding="utf-8")
        mismatch = self.delivery("gateway-task-bundle", "delivery/gateway-response.md")
        self.assertIn("bundled_tool_mismatch", mismatch.stderr)
        scope.write_bytes((ROOT / "scripts/patch_pack_scope.py").read_bytes())
        planner = self.temp / "planner"
        (planner / "scripts").mkdir(parents=True)
        for name in ("validate-patch-pack.py", "patch_pack_scope.py", "verify-agent-evidence.py", "verify-agent-result.sh"):
            shutil.copy2(ROOT / "scripts" / name, planner / "scripts" / name)
        (planner / "VERSION").write_text("1.3.0\n", encoding="utf-8")
        bad = b"#!/usr/bin/env bash\nexit 7\n"
        (self.pack / "scripts/verify-agent-result.sh").write_bytes(bad)
        (planner / "scripts/verify-agent-result.sh").write_bytes(bad)
        failure = self.delivery("gateway-task-bundle", "delivery/gateway-response.md", planner=planner)
        self.assertIn("bundled_tool_startup_failed", failure.stderr)

    def test_templates_and_docs_use_canonical_handoff_without_stale_normative_prompt(self) -> None:
        self.assertTrue((ROOT / "templates/executable-patch-pack/AGENT_HANDOFF.md").is_file())
        template_handoff = ROOT / "templates/executable-patch-pack/AGENT_HANDOFF.md"
        template_alias = ROOT / "templates/executable-patch-pack/AGENT_PROMPT.md"
        self.assertTrue(template_alias.is_file())
        self.assertEqual(template_alias.read_bytes(), template_handoff.read_bytes())
        for relative in (
            "docs/PATCH_PACK_FORMAT.md",
            "docs/PATCH_PACK_HANDOFF.md",
            "docs/GATEWAY_INTEROPERABILITY.md",
            "docs/STRUCTURED_FORMAT_POLICY.md",
            "prompts/GPT_CREATE_PATCH_PACK.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("AGENT_HANDOFF.md", text)
        self.assertIn("YAML is not a canonical", (ROOT / "docs/STRUCTURED_FORMAT_POLICY.md").read_text(encoding="utf-8"))


class GatewayEvidencePreparationTests(unittest.TestCase):
    def setUp(self) -> None:
        import hashlib
        self.root = Path(tempfile.mkdtemp())
        self.repo = self.root / "repo"
        self.pack = self.root / "pack"
        self.repo.mkdir()
        self.pack.mkdir()
        run("git", "-C", str(self.repo), "init", "-q")
        run("git", "-C", str(self.repo), "config", "user.name", "Test")
        run("git", "-C", str(self.repo), "config", "user.email", "test@example.com")
        (self.repo / "file.txt").write_text("base\n", encoding="utf-8")
        run("git", "-C", str(self.repo), "add", ".")
        run("git", "-C", str(self.repo), "commit", "-qm", "base")
        self.base = run("git", "-C", str(self.repo), "rev-parse", "HEAD").stdout.strip()
        content = b"implementation\nproof\n"
        (self.repo / "file.txt").write_bytes(content)
        run("git", "-C", str(self.repo), "add", "file.txt")
        run("git", "-C", str(self.repo), "commit", "-qm", "implementation")
        self.implementation = run("git", "-C", str(self.repo), "rev-parse", "HEAD").stdout.strip()
        self.patch_id = "patch-20260728-121500-gateway-evidence"
        self.evidence_rel = Path(".gpt-review/evidence/v1.2.0") / self.patch_id
        manifest = {
            "schema_version": 2,
            "patch_id": self.patch_id,
            "title": "Gateway evidence fixture",
            "description": "Exercises generated evidence preparation.",
            "created_at": "2026-07-28T12:15:00Z",
            "patch_timestamp": "20260728-121500",
            "patch_slug": "gateway-evidence",
            "baseline_release": "v1.2.0",
            "evidence_directory": self.evidence_rel.as_posix(),
            "workflow": {"repository": "https://github.com/rceman/gpt-review-planner", "version": "v1.3.0", "commit": self.base, "document": "GPT_REVIEW_PLANNER.md"},
            "target": {"repository": "example/evidence", "branch": "main", "base_revision": self.base},
            "files_created": [], "files_modified": ["file.txt"], "files_deleted": [],
            "requirements": [{"id": "REQ-1", "summary": "Modify file", "acceptance": ["File contains proof."]}],
            "gates": [{"id": "unit", "name": "Unit", "kind": "command", "command": "true"}],
            "gpt_static_checks_performed": ["static"], "gpt_runtime_checks_not_performed": ["runtime"],
            "known_integration_risks": [], "forbidden_deviations": []
        }
        self.manifest_raw = json.dumps(manifest, indent=2) + "\n"
        (self.pack / "manifest.json").write_text(self.manifest_raw, encoding="utf-8")
        directory = self.repo / self.evidence_rel
        directory.mkdir(parents=True)
        (directory / "manifest.json").write_text(self.manifest_raw, encoding="utf-8")
        digest = hashlib.sha256(content).hexdigest()
        evidence = {
            "schema_version": 1,
            "implementation_commit": self.implementation,
            "requirements": [{"id": "REQ-1", "status": "pass", "proofs": [{"kind": "source", "path": "file.txt", "lines": [1, 2], "sha256": digest, "symbol": "proof"}]}],
            "gates": [{"id": "unit", "status": "pass", "exit": 0, "tests": 1, "summary": "pass"}],
            "deviations": []
        }
        (directory / "evidence.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def verify(self, mode: str, evidence_commit: str | None = None) -> subprocess.CompletedProcess[str]:
        args = ["python3", str(ROOT / "scripts/verify-agent-evidence.py"), mode, "--pack", str(self.pack), "--repo", str(self.repo), "--implementation-commit", self.implementation]
        if evidence_commit:
            args += ["--evidence-commit", evidence_commit]
        return run(*args)

    def test_prepare_accepts_exact_two_untracked_or_staged_generated_files(self) -> None:
        untracked = self.verify("prepare")
        self.assertEqual(untracked.returncode, 0, untracked.stderr)
        run("git", "-C", str(self.repo), "add", self.evidence_rel.as_posix())
        staged = self.verify("prepare")
        self.assertEqual(staged.returncode, 0, staged.stderr)

    def test_prepare_rejects_third_file_and_wrong_directory(self) -> None:
        extra = self.repo / self.evidence_rel / "extra.json"
        extra.write_text("{}\n", encoding="utf-8")
        result = self.verify("prepare")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("path mismatch", result.stderr)
        extra.unlink()
        wrong = self.repo / ".gpt-review/evidence/wrong/evidence.json"
        wrong.parent.mkdir(parents=True)
        wrong.write_text("{}\n", encoding="utf-8")
        result = self.verify("prepare")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("extra", result.stderr)

    def test_committed_requires_direct_parent_and_exact_two_files(self) -> None:
        run("git", "-C", str(self.repo), "add", self.evidence_rel.as_posix())
        self.assertEqual(self.verify("prepare").returncode, 0)
        run("git", "-C", str(self.repo), "commit", "-qm", "evidence")
        evidence_commit = run("git", "-C", str(self.repo), "rev-parse", "HEAD").stdout.strip()
        valid = self.verify("committed", evidence_commit)
        self.assertEqual(valid.returncode, 0, valid.stderr)
        run("git", "-C", str(self.repo), "checkout", "-q", self.implementation)
        (self.repo / "unrelated.txt").write_text("bad\n", encoding="utf-8")
        run("git", "-C", str(self.repo), "add", "unrelated.txt")
        run("git", "-C", str(self.repo), "commit", "-qm", "intermediate")
        run("git", "-C", str(self.repo), "cherry-pick", "-q", evidence_commit)
        wrong_commit = run("git", "-C", str(self.repo), "rev-parse", "HEAD").stdout.strip()
        invalid = self.verify("committed", wrong_commit)
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("committed evidence scope mismatch", invalid.stderr)

    def test_committed_rejects_missing_or_modified_manifest_and_source_changes(self) -> None:
        directory = self.repo / self.evidence_rel
        (directory / "manifest.json").write_text("{}\n", encoding="utf-8")
        run("git", "-C", str(self.repo), "add", self.evidence_rel.as_posix())
        result = self.verify("prepare")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("byte-identical", result.stderr)
        (directory / "manifest.json").write_text(self.manifest_raw, encoding="utf-8")
        (self.repo / "source-extra.txt").write_text("bad\n", encoding="utf-8")
        result = self.verify("prepare")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("extra", result.stderr)


if __name__ == "__main__":
    unittest.main()
