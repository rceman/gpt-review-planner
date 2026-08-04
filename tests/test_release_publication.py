from __future__ import annotations

import importlib.util
import json
import os
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
        self.assertEqual(schema["oneOf"][0]["properties"]["mode"]["const"], "none")
        self.assertEqual(schema["oneOf"][1]["properties"]["mode"]["enum"], ["tag_only", "github_actions"])
        self.assertFalse(schema["oneOf"][0]["additionalProperties"])
        self.assertFalse(schema["oneOf"][1]["additionalProperties"])

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
        (repo / "release-publication.json").write_text(
            (ROOT / f"fixtures/release-publication/{fixture_name or mode}/release-publication.json").read_text()
        )
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
