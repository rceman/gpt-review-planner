from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_PATH = ROOT / "scripts" / "validate-release-publication.py"
VERIFIER_PATH = ROOT / "scripts" / "verify-release-publication.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("publication_validator", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def git(cwd: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=cwd, text=True, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, check=False)
    if completed.returncode:
        raise AssertionError(f"git {' '.join(args)} failed: {completed.stderr}")
    return completed.stdout.strip()


def run_script(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(script), *args], cwd=ROOT, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env, check=False)


class FakeGitHub(BaseHTTPRequestHandler):
    payloads: dict[str, Any] = {}
    requests: list[str] = []

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler API
        type(self).requests.append(self.path)
        value = type(self).payloads.get(self.path)
        if value is None:
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(value).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        return


class ReleasePublicationTests(unittest.TestCase):
    def test_schema_is_strict_and_declares_the_three_modes(self) -> None:
        schema = json.loads((ROOT / "schemas/release-publication.schema.json").read_text())
        self.assertEqual(
            [item["$ref"] for item in schema["oneOf"]],
            [
                "#/$defs/none",
                "#/$defs/tag_only_no_workflow",
                "#/$defs/tag_only_workflow",
                "#/$defs/github_actions_no_assets",
                "#/$defs/github_actions_assets",
            ],
        )
        self.assertEqual(schema["$defs"]["none"]["properties"]["mode"]["const"], "none")
        self.assertFalse(schema["$defs"]["active"]["additionalProperties"])
        self.assertEqual(schema["$defs"]["tag_only_no_workflow"]["allOf"][1]["properties"]["workflow"]["type"], "null")
        self.assertEqual(
            schema["$defs"]["tag_only_workflow"]["allOf"][1]["properties"]["tag_push_side_effects"]["const"],
            ["tag_ci"],
        )
        self.assertEqual(
            schema["$defs"]["github_actions_no_assets"]["allOf"][1]["properties"]["tag_push_side_effects"]["const"],
            ["tag_ci", "github_release_create_or_update"],
        )
        self.assertEqual(
            schema["$defs"]["github_actions_assets"]["allOf"][1]["properties"]["tag_push_side_effects"]["const"],
            ["tag_ci", "github_release_create_or_update", "asset_upload"],
        )

    def test_schema_and_templates_have_mode_specific_parity(self) -> None:
        schema = json.loads((ROOT / "schemas/release-publication.schema.json").read_text())
        definitions = schema["$defs"]
        paths = [
            ROOT / "fixtures/release-publication/none/release-publication.json",
            ROOT / "fixtures/release-publication/gpt-tunnel-gateway/release-publication.json",
            ROOT / "fixtures/release-publication/gpt-review-planner/release-publication.json",
            ROOT / "templates/project/release-publication.none.json",
            ROOT / "templates/project/release-publication.tag_only.json",
            ROOT / "templates/project/release-publication.github_actions.json",
        ]
        for path in paths:
            with self.subTest(path=path):
                repo_root = path.parent if "fixtures/release-publication" in path.as_posix() else None
                data = validator.load_publication_declaration(path, repo_root=repo_root)
                self.assertIn(data["mode"], {"none", "tag_only", "github_actions"})
                if data["mode"] == "none":
                    self.assertEqual(data, {"schema_version": 1, "mode": "none"})
                    self.assertIn("none", definitions)
                elif data["mode"] == "tag_only" and data["workflow"] is None:
                    self.assertEqual(
                        definitions["tag_only_no_workflow"]["allOf"][1]["properties"]["proof_requirements"]["$ref"],
                        "#/$defs/proofs_tag_only_none",
                    )
                    self.assertFalse(data["proof_requirements"]["tag_ci"])
                    self.assertEqual(data["tag_push_side_effects"], [])
                elif data["mode"] == "tag_only":
                    self.assertEqual(data["workflow"]["purpose"], "tag_validation")
                    self.assertEqual(data["workflow"]["permissions"]["contents"], "read")
                    self.assertEqual(data["tag_push_side_effects"], ["tag_ci"])
                    self.assertEqual(data["proof_requirements"]["release_metadata"], False)
                elif data["assets"]["expected"]:
                    self.assertEqual(data["workflow"]["purpose"], "release_publication")
                    self.assertEqual(data["workflow"]["permissions"]["contents"], "write")
                    self.assertEqual(data["tag_push_side_effects"], ["tag_ci", "github_release_create_or_update", "asset_upload"])
                    self.assertTrue(data["proof_requirements"]["assets"])
                else:
                    self.assertEqual(data["workflow"]["permissions"]["contents"], "write")
                    self.assertEqual(data["tag_push_side_effects"], ["tag_ci", "github_release_create_or_update"])
                    self.assertFalse(data["proof_requirements"]["assets"])

    def test_none_fixture_is_exact_and_valid(self) -> None:
        path = ROOT / "fixtures/release-publication/none/release-publication.json"
        self.assertEqual(validator.load_publication_declaration(path)["mode"], "none")
        with self.assertRaises(validator.PublicationError):
            validator.validate_declaration({"schema_version": 1, "mode": "none", "workflow": {}})

    def test_gateway_tag_only_fixture_scans_workflow(self) -> None:
        base = ROOT / "fixtures/release-publication/gpt-tunnel-gateway"
        declaration = validator.load_publication_declaration(base / "release-publication.json", repo_root=base)
        self.assertEqual(declaration["mode"], "tag_only")
        self.assertEqual(declaration["workflow"]["permissions"]["contents"], "read")
        self.assertEqual(declaration["workflow"]["name"], "CI")
        self.assertEqual(declaration["workflow"]["path"], ".github/workflows/ci.yml")
        self.assertEqual(declaration["workflow"]["tag_trigger"], "unfiltered_push")

    def test_planner_github_actions_fixture_scans_release_and_token(self) -> None:
        base = ROOT / "fixtures/release-publication/gpt-review-planner"
        declaration = validator.load_publication_declaration(base / "release-publication.json", repo_root=base)
        self.assertEqual(declaration["mode"], "github_actions")
        self.assertTrue(declaration["github_release"]["expected"])
        self.assertEqual(declaration["credential_authority"], "github.token")
        self.assertEqual(declaration["workflow"]["name"], "Build Offline Rust Toolchain")
        self.assertEqual(declaration["workflow"]["path"], ".github/workflows/build-offline-rust.yml")
        self.assertEqual(declaration["workflow"]["tag_trigger"], "explicit_tags_filter")

    def test_duplicate_keys_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "release-publication.json"
            path.write_text('{"schema_version":1,"mode":"none","mode":"tag_only"}')
            with self.assertRaises(validator.PublicationError):
                validator.load_publication_declaration(path)

    def test_active_declaration_requires_complete_authorization_shape(self) -> None:
        base = json.loads((ROOT / "fixtures/release-publication/gpt-review-planner/release-publication.json").read_text())
        base["credential_authority"] = "none"
        with self.assertRaises(validator.PublicationError):
            validator.validate_declaration(base)
        base = json.loads((ROOT / "fixtures/release-publication/gpt-tunnel-gateway/release-publication.json").read_text())
        base["workflow"]["tag_patterns"] = ["v*"]
        with self.assertRaises(validator.PublicationError):
            validator.validate_declaration(base)

    def test_workflow_digest_and_name_are_bound(self) -> None:
        base = ROOT / "fixtures/release-publication/gpt-tunnel-gateway"
        data = json.loads((base / "release-publication.json").read_text())
        data["workflow"]["name"] = "Other"
        with self.assertRaises(validator.PublicationError):
            validator.validate_declaration(data, repo_root=base)

    def _tagged_repo(self, mode: str) -> tuple[tempfile.TemporaryDirectory[str], Path, str]:
        temp = tempfile.TemporaryDirectory()
        repo = Path(temp.name)
        git(repo, "init", "-q")
        git(repo, "config", "user.email", "test@example.invalid")
        git(repo, "config", "user.name", "Test")
        (repo / "VERSION").write_text("2.2.0\n")
        fixture_name = {"gateway": "gpt-tunnel-gateway", "planner": "gpt-review-planner"}.get(mode)
        declaration_source = (
            ROOT / f"fixtures/release-publication/{fixture_name}/release-publication.json"
            if fixture_name
            else ROOT / "templates/project/release-publication.tag_only.json"
            if mode == "tag_only_null"
            else ROOT / f"fixtures/release-publication/{mode}/release-publication.json"
        )
        (repo / "release-publication.json").write_text(declaration_source.read_text())
        workflow = repo / ".github/workflows"
        workflow.mkdir(parents=True)
        destination = None
        if fixture_name is not None:
            source_name = "ci.yml" if mode == "gateway" else "build-offline-rust.yml"
            source = ROOT / f"fixtures/release-publication/{fixture_name}/.github/workflows/{source_name}"
            destination = workflow / source.name
            destination.write_bytes(source.read_bytes())
        # Fixture declarations intentionally use their own workflow digest.
        data = json.loads((repo / "release-publication.json").read_text())
        import hashlib
        if destination is not None:
            data["workflow"]["sha256"] = hashlib.sha256(destination.read_bytes()).hexdigest()
        (repo / "release-publication.json").write_text(json.dumps(data, indent=2) + "\n")
        git(repo, "add", ".")
        git(repo, "commit", "-qm", "fixture")
        sha = git(repo, "rev-parse", "HEAD")
        git(repo, "tag", "-a", "v2.2.0", "-m", "v2.2.0")
        return temp, repo, sha

    def _write_declaration_with_workflow(self, root: Path, workflow_text: str, declaration: dict[str, Any]) -> Path:
        workflow = root / ".github/workflows/build-offline-rust.yml"
        workflow.parent.mkdir(parents=True, exist_ok=True)
        workflow.write_text(workflow_text, encoding="utf-8")
        declaration["workflow"]["sha256"] = __import__("hashlib").sha256(workflow.read_bytes()).hexdigest()
        path = root / "release-publication.json"
        path.write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
        return path

    def test_verifier_none_makes_no_network_request(self) -> None:
        temp, repo, sha = self._tagged_repo("none")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.payloads = {}
        handler.requests = []
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        completed = run_script(VERIFIER_PATH, "--repo", str(repo),
                               "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["state"], "not_applicable")
        self.assertEqual(handler.requests, [])
        self.assertTrue(sha)

    def test_verifier_tag_only_uses_distinct_successful_run(self) -> None:
        temp, repo, sha = self._tagged_repo("gateway")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.requests = []
        handler.payloads = {
            "/repos/acme/gateway/actions/runs?event=push&per_page=100": {
                "workflow_runs": [{"id": 41, "name": "CI", "path": ".github/workflows/ci.yml",
                                    "head_sha": sha, "ref": "refs/heads/stale", "head_branch": "v2.2.0", "event": "push",
                                    "status": "completed", "conclusion": "success", "created_at": "2026-08-01T00:00:01Z",
                                    "html_url": "https://example.invalid/run/41"}]
            },
            "/repos/acme/gateway/actions/runs/41/jobs?per_page=100": {
                "jobs": [{"id": 51, "html_url": "https://example.invalid/job/51", "status": "completed", "conclusion": "success"}]
            },
        }
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        completed = run_script(VERIFIER_PATH, "--repo", str(repo), "--repository", "acme/gateway",
                               "--tag", "v2.2.0", "--created-after", "2026-07-31T23:59:59Z",
                               "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["run_id"], 41)
        self.assertEqual(result["job_id"], 51)

    def test_tag_only_without_workflow_is_successful_without_network(self) -> None:
        temp, repo, sha = self._tagged_repo("tag_only_null")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.payloads = {}
        handler.requests = []
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        completed = run_script(
            VERIFIER_PATH,
            "--repo", str(repo),
            "--tag", "v2.2.0",
            "--api-url", f"http://127.0.0.1:{server.server_port}",
            "--format", "json",
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "success")
        self.assertFalse(result["blocking"])
        self.assertEqual(result["checked_sha"], sha)
        self.assertEqual(handler.requests, [])

    def test_active_unavailable_publication_is_blocking(self) -> None:
        temp, repo, sha = self._tagged_repo("gateway")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.payloads = {}
        handler.requests = []
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.shutdown)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.server_close)
        completed = run_script(
            VERIFIER_PATH,
            "--repo", str(repo), "--repository", "acme/gateway", "--tag", "v2.2.0",
            "--created-after", "2026-07-31T23:59:59Z",
            "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json",
        )
        self.assertEqual(completed.returncode, 4)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "unavailable")
        self.assertTrue(result["blocking"])
        self.assertTrue(sha)

    def test_upload_only_workflow_is_rejected_for_create_or_update(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = (ROOT / "fixtures/release-publication/gpt-review-planner/.github/workflows/build-offline-rust.yml").read_text()
            workflow = re.sub(
                r"if gh release view.*?\n.*?gh release upload",
                "gh release upload",
                source,
                flags=re.DOTALL,
            )
            workflow = workflow.replace("          else\n", "")
            declaration = json.loads((ROOT / "fixtures/release-publication/gpt-review-planner/release-publication.json").read_text())
            path = self._write_declaration_with_workflow(root, workflow, declaration)
            with self.assertRaises(validator.PublicationError):
                validator.load_publication_declaration(path, repo_root=root)

    def test_workflow_notes_and_release_flags_must_match_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = (ROOT / "fixtures/release-publication/gpt-review-planner/.github/workflows/build-offline-rust.yml").read_text()
            workflow = source.replace("--generate-notes", "--notes-file CHANGELOG.md").replace("--clobber", "")
            declaration = json.loads((ROOT / "fixtures/release-publication/gpt-review-planner/release-publication.json").read_text())
            path = self._write_declaration_with_workflow(root, workflow, declaration)
            with self.assertRaises(validator.PublicationError):
                validator.load_publication_declaration(path, repo_root=root)

    def test_nested_or_ambiguous_workflow_markers_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = (ROOT / "fixtures/release-publication/gpt-tunnel-gateway/.github/workflows/ci.yml").read_text()
            workflow = source.replace("permissions:\n", "  nested:\n    push:\npermissions:\n")
            path = root / ".github/workflows/ci.yml"
            path.parent.mkdir(parents=True)
            path.write_text(workflow, encoding="utf-8")
            with self.assertRaises(validator.PublicationError):
                validator.scan_workflow(path)

    def test_publication_errors_are_path_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            declaration = Path(temp) / "release-publication.json"
            declaration.write_text("{not-json", encoding="utf-8")
            completed = run_script(VALIDATOR_PATH, str(declaration), "--repo", temp)
            self.assertNotEqual(completed.returncode, 0)
            self.assertNotIn(temp, completed.stderr)

    def test_setup_managed_block_matches_publication_contract(self) -> None:
        clauses = (
            "python3 scripts/validate-release-publication.py release-publication.json --repo .",
            "git push origin refs/tags/v<TARGET_VERSION>:refs/tags/v<TARGET_VERSION>",
            "none` has no publication task",
            "tag_only` verifies declared tag CI",
            "github_actions` verifies the declared publication workflow plus GitHub Release/assets",
            "Owner authorization to push the exact tag includes only declaration-authorized automatic workflow side effects",
            "Local `gh`, curl, wget, `GH_TOKEN`, and `GITHUB_TOKEN` publication is forbidden",
        )
        template = (ROOT / "templates/project/AGENTS.managed-block.md").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as temp:
            project = Path(temp) / "project"
            project.mkdir()
            completed = subprocess.run(
                [
                    "bash", str(ROOT / "setup.sh"), "--project", str(project), "--version", "v2.2.2",
                    "--commit", "a" * 40, "--execution-mode", "gpt_tunnel_managed",
                    "--release-publication-file", str(ROOT / "templates/project/release-publication.none.json"),
                ],
                cwd=ROOT, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            rendered = (project / "AGENTS.md").read_text(encoding="utf-8")
        for clause in clauses:
            with self.subTest(clause=clause):
                self.assertIn(clause, template)
                self.assertIn(clause, rendered)
        self.assertNotIn("Do not publish a GitHub Release without explicit authorization", template)
        self.assertNotIn("Do not publish a GitHub Release without explicit authorization", rendered)

    def test_verifier_github_actions_checks_release_and_assets(self) -> None:
        temp, repo, sha = self._tagged_repo("planner")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.requests = []
        handler.payloads = {
            "/repos/acme/planner/actions/runs?event=push&per_page=100": {
                "workflow_runs": [{"id": 42, "name": "Build Offline Rust Toolchain", "path": ".github/workflows/build-offline-rust.yml",
                                    "head_sha": sha, "ref": "refs/tags/v2.2.0", "head_branch": "v2.2.0", "event": "push",
                                    "status": "completed", "conclusion": "success", "created_at": "2026-08-01T00:00:01Z",
                                    "html_url": "https://example.invalid/run/42"}]
            },
            "/repos/acme/planner/actions/runs/42/jobs?per_page=100": {"jobs": [{"id": 52, "html_url": "https://example.invalid/job/52"}]},
            "/repos/acme/planner/releases/tags/v2.2.0": {"id": 99, "tag_name": "v2.2.0", "draft": False, "prerelease": False},
            "/repos/acme/planner/releases/99/assets?per_page=100": [
                {"name": "rustc-lite.tar.zst"}, {"name": "rustc-lite.sha256"}, {"name": "rustc-lite.json"}
            ],
        }
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        completed = run_script(VERIFIER_PATH, "--repo", str(repo), "--repository", "acme/planner",
                               "--tag", "v2.2.0", "--created-after", "2026-07-31T23:59:59Z",
                               "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["state"], "success")
        self.assertEqual(result["release_id"], 99)
        self.assertEqual(result["asset_names"], ["rustc-lite.tar.zst", "rustc-lite.sha256", "rustc-lite.json"])

    def test_verifier_rejects_failed_run_without_publication_request(self) -> None:
        temp, repo, sha = self._tagged_repo("gateway")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.requests = []
        handler.payloads = {
            "/repos/acme/gateway/actions/runs?event=push&per_page=100": {
                "workflow_runs": [{"id": 43, "name": "CI", "path": ".github/workflows/ci.yml",
                                    "head_sha": sha, "ref": "refs/tags/v2.2.0", "head_branch": "v2.2.0", "event": "push",
                                    "status": "completed", "conclusion": "failure",
                                    "created_at": "2026-08-01T00:00:00Z"}]
            }
        }
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        completed = run_script(VERIFIER_PATH, "--repo", str(repo), "--repository", "acme/gateway",
                               "--tag", "v2.2.0", "--created-after", "2026-07-31T23:59:59Z",
                               "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json")
        self.assertEqual(completed.returncode, 3)
        self.assertEqual(json.loads(completed.stdout)["state"], "failed")
        self.assertEqual(len(handler.requests), 1)

    def test_verifier_normalizes_integer_run_ids_for_exclusion(self) -> None:
        temp, repo, sha = self._tagged_repo("gateway")
        self.addCleanup(temp.cleanup)
        handler = type("Handler", (FakeGitHub,), {})
        handler.requests = []
        handler.payloads = {
            "/repos/acme/gateway/actions/runs?event=push&per_page=100": {
                "workflow_runs": [{"id": 41, "name": "CI", "path": ".github/workflows/ci.yml",
                                    "head_sha": sha, "head_branch": "v2.2.0", "event": "push",
                                    "status": "completed", "conclusion": "success",
                                    "created_at": "2026-08-01T00:00:01Z"}]
            }
        }
        server = HTTPServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(thread.join, 2)
        self.addCleanup(server.shutdown)
        completed = run_script(VERIFIER_PATH, "--repo", str(repo), "--repository", "acme/gateway",
                               "--tag", "v2.2.0", "--created-after", "2026-07-31T23:59:59Z",
                               "--exclude-run-id", "41", "--api-url", f"http://127.0.0.1:{server.server_port}", "--format", "json")
        self.assertEqual(completed.returncode, 5)
        self.assertEqual(json.loads(completed.stdout)["state"], "invalid_response")


if __name__ == "__main__":
    unittest.main()
