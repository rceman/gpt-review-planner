from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_validator(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EngineeringBaselineTests(unittest.TestCase):
    def test_required_tree_and_catalog_pass(self) -> None:
        required = [
            "docs/engineering/README.md", "docs/engineering/NORMATIVE_RULES.md",
            "docs/engineering/STACK_POLICY.md", "docs/engineering/PROJECT_STRUCTURE.md",
            "docs/engineering/TEMPLATE_REPOSITORY_CONTRACT.md", "docs/engineering/PROJECT_EXCEPTIONS.md",
            "docs/engineering/DEPENDENCY_POLICY.md", "docs/engineering/PERFORMANCE_BASELINE.md",
            "docs/engineering/SECURITY_BASELINE.md", "docs/engineering/CONFIGURATION_AND_SECRETS.md",
            "docs/engineering/OBSERVABILITY.md", "docs/engineering/API_CONTRACTS.md",
            "docs/engineering/TESTING_BASELINE.md", "profiles/engineering/rules.json",
            "profiles/engineering/catalog.json", "schemas/engineering-rules.schema.json",
            "schemas/engineering-catalog.schema.json", "schemas/engineering-project-profile.schema.json",
            "schemas/project-engineering-declaration.schema.json",
            "templates/project/engineering-profile.example.json",
            "scripts/validate-engineering-catalog.py", "scripts/validate-project-engineering-profile.py",
        ]
        for path in required:
            self.assertTrue((ROOT / path).is_file(), path)
            self.assertTrue((ROOT / path).stat().st_size > 0, path)
        result = subprocess.run(["python3", str(ROOT / "scripts/validate-engineering-catalog.py")], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS:", result.stdout)

    def test_catalog_rejects_duplicate_missing_anchor_and_conflict(self) -> None:
        validator = load_validator("catalog_validator", ROOT / "scripts/validate-engineering-catalog.py")
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            rules_path = copy / "profiles/engineering/rules.json"
            rules = json.loads(rules_path.read_text())
            duplicate = json.loads(json.dumps(rules))
            duplicate["rules"].append(duplicate["rules"][0])
            rules_path.write_text(json.dumps(duplicate))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)
            rules_path.write_text(json.dumps(rules))
            broken = json.loads(json.dumps(rules))
            broken["rules"][0]["anchor"] = "MISSING-ANCHOR"
            rules_path.write_text(json.dumps(broken))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)
            for mutation in (
                lambda data: data["rules"][0].update({"level": "invalid"}),
                lambda data: data["rules"][0].update({"category": "invalid"}),
                lambda data: data["rules"][0].update({"replacement": "UNKNOWN-001"}),
                lambda data: data["rules"][0].update({"replacement": data["rules"][0]["id"]}),
                lambda data: data["rules"][0].update({"document": "/absolute/path.md"}),
                lambda data: data["rules"][0].update({"anchor": "bad\x00anchor"}),
            ):
                candidate = json.loads(json.dumps(rules))
                mutation(candidate)
                rules_path.write_text(json.dumps(candidate))
                with self.assertRaises(validator.CatalogError):
                    validator.validate(copy)
            cycle = json.loads(json.dumps(rules))
            cycle["rules"][0]["replacement"] = cycle["rules"][1]["id"]
            cycle["rules"][1]["replacement"] = cycle["rules"][0]["id"]
            rules_path.write_text(json.dumps(cycle))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)
            rules_path.write_text(json.dumps(rules))
            conflict = json.loads(json.dumps(rules))
            definition = copy / "profiles/engineering/projects/fullstack-rust-sveltekit.json"
            profile = json.loads(definition.read_text())
            profile["forbidden_rule_ids"].append(profile["required_rule_ids"][0])
            definition.write_text(json.dumps(profile))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

    def _run_profile(self, project: Path, *extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["python3", str(ROOT / "scripts/validate-project-engineering-profile.py"),
             str(project / "engineering-profile.json"), "--project-root", str(project),
             "--planner-root", str(ROOT), *extra], capture_output=True, text=True
        )

    def _project(self, root: Path, declaration: object | None = None) -> Path:
        project = root / f"project-{len(list(root.iterdir()))}"
        project.mkdir()
        lock = {"schema_version": 1, "repository": "https://github.com/rceman/gpt-review-planner", "version": "v1.1.1", "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(), "document": "GPT_REVIEW_PLANNER.md", "execution_mode": "repository_evidence", "installed_at": "2026-07-25T00:00:00Z"}
        (project / ".gpt-workflow.lock").write_text(json.dumps(lock))
        if declaration is not None:
            (project / "engineering-profile.json").write_text(json.dumps(declaration))
        return project

    def test_project_declaration_cases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = {"schema_version": 1, "workflow_lock_path": ".gpt-workflow.lock", "profile_id": "legacy-python-service", "exceptions": [{"id": "legacy-python-production-backend", "rule_id": "STACK-PYTHON-001", "reason": "Existing deployed service", "scope": "Current backend", "approved_by": "owner", "migration_target": "rust-axum", "migration_required": False, "expires_at": None}]}
            project = self._project(root, valid)
            result = self._run_profile(project)
            self.assertEqual(result.returncode, 0, result.stderr)
            project_missing = root / "missing"
            project_missing.mkdir()
            lock = json.loads((project / ".gpt-workflow.lock").read_text())
            (project_missing / ".gpt-workflow.lock").write_text(json.dumps(lock))
            self.assertNotEqual(self._run_profile(project_missing).returncode, 0)
            self.assertEqual(self._run_profile(project_missing, "--allow-missing").returncode, 0)
            unknown = json.loads(json.dumps(valid)); unknown["profile_id"] = "unknown-profile"
            unknown_project = self._project(root, unknown)
            self.assertNotEqual(self._run_profile(unknown_project).returncode, 0)
            expired = json.loads(json.dumps(valid)); expired["exceptions"][0]["expires_at"] = "2020-01-01T00:00:00Z"
            expired_project = self._project(root, expired)
            self.assertNotEqual(self._run_profile(expired_project, "--now", "2026-01-01T00:00:00Z").returncode, 0)
            mismatch_project = self._project(root, valid)
            mismatch_lock = json.loads((mismatch_project / ".gpt-workflow.lock").read_text())
            mismatch_lock["commit"] = "0" * 40
            (mismatch_project / ".gpt-workflow.lock").write_text(json.dumps(mismatch_lock))
            self.assertNotEqual(self._run_profile(mismatch_project).returncode, 0)
            controls = json.loads(json.dumps(valid)); controls["exceptions"][0]["reason"] = "bad\x00reason"
            controls_project = self._project(root, controls)
            self.assertNotEqual(self._run_profile(controls_project).returncode, 0)

    def test_semantic_policy_contract(self) -> None:
        stack = (ROOT / "docs/engineering/STACK_POLICY.md").read_text()
        python = (ROOT / "docs/engineering/languages/PYTHON.md").read_text()
        database = (ROOT / "docs/engineering/database/LIQUIBASE.md").read_text()
        template = (ROOT / "docs/engineering/TEMPLATE_REPOSITORY_CONTRACT.md").read_text()
        primary = (ROOT / "prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md").read_text()
        agents = (ROOT / "templates/project/AGENTS.managed-block.md").read_text()
        installer = (ROOT / "setup.sh").read_text()
        for phrase in ("SvelteKit", "Rust", "Axum", "Go", "Gin", "Node.js", "forbidden", "PostgreSQL", "Liquibase"):
            self.assertIn(phrase, stack)
        for phrase in ("pyproject.toml", "Ruff", "Pyright", "pytest", "subprocess", "legacy-python-service"):
            self.assertIn(phrase, python)
        for phrase in ("one root", "immutable", "startup", "preconditions", "Liquibase"):
            self.assertIn(phrase, database)
        self.assertIn(".gpt-workflow.lock", template)
        self.assertIn("engineering-profile.json", primary)
        self.assertIn("PostgreSQL schema authority remains Liquibase", agents)
        for phrase in ("engineering-profile.json", "Rust/Axum", "Go/Gin", "Liquibase", "legacy"):
            self.assertIn(phrase, agents)
            self.assertIn(phrase, installer)

    def test_catalog_freshness_capability_and_archive_ordering_contracts(self) -> None:
        validator = load_validator("catalog_validator_freshness", ROOT / "scripts/validate-engineering-catalog.py")
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / "repo"
            shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__"))
            metadata_path = copy / "profiles/engineering/source-metadata.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["documents"][0]["last_reviewed"] = "2099-01-01"
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy, __import__("datetime").date(2026, 7, 25))
            metadata["documents"][0]["last_reviewed"] = "2026-07-25"
            metadata_path.write_text(json.dumps(metadata))
            rules = json.loads((copy / "profiles/engineering/rules.json").read_text())
            rules["rules"][0]["applies_to"] = ["capability:not-a-capability"]
            (copy / "profiles/engineering/rules.json").write_text(json.dumps(rules))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

            rules = json.loads((copy / "profiles/engineering/rules.json").read_text())
            rules["rules"][0]["applies_to"] = ["capability:frontend"]
            profile_path = copy / "profiles/engineering/projects/sveltekit-frontend.json"
            profile = json.loads(profile_path.read_text())
            profile["required_rule_ids"].remove("STACK-FRONTEND-001")
            profile_path.write_text(json.dumps(profile))
            (copy / "profiles/engineering/rules.json").write_text(json.dumps(rules))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)
            profile["required_rule_ids"].append("STACK-FRONTEND-001")
            profile["forbidden_rule_ids"].remove("STACK-NODE-001")
            profile_path.write_text(json.dumps(profile))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

            profile["forbidden_rule_ids"].append("STACK-NODE-001")
            profile["template_contract"]["forbidden_paths"] = ["../escape"]
            profile_path.write_text(json.dumps(profile))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)
            profile["template_contract"]["forbidden_paths"] = ["node-backend"]
            profile_path.write_text(json.dumps(profile))
            orphan = copy / "profiles/engineering/projects/orphan.json"
            orphan.write_text(json.dumps(profile))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

            metadata_path = copy / "profiles/engineering/source-metadata.json"
            metadata = json.loads(metadata_path.read_text())
            metadata["documents"][0]["source_domains"] = ["example.com"]
            metadata_path.write_text(json.dumps(metadata))
            orphan.unlink()
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

            example_path = copy / "templates/project/engineering-profile.example.json"
            example = json.loads(example_path.read_text())
            example["unexpected"] = True
            example_path.write_text(json.dumps(example))
            metadata["documents"][0]["source_domains"] = ["doc.rust-lang.org", "rust-lang.github.io", "tokio.rs", "docs.rs"]
            metadata_path.write_text(json.dumps(metadata))
            with self.assertRaises(validator.CatalogError):
                validator.validate(copy)

    def test_declaration_path_and_lock_contract_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = {"schema_version": 1, "workflow_lock_path": ".gpt-workflow.lock", "profile_id": "legacy-python-service", "exceptions": [{"id": "legacy-python-production-backend", "rule_id": "STACK-PYTHON-001", "reason": "Existing deployed service", "scope": "Current backend", "approved_by": "owner", "migration_target": "rust-axum", "migration_required": False, "expires_at": None}]}
            for unsafe in ("/tmp/lock", "C:\\lock", "\\\\server\\lock", "file:///tmp/lock", "a\\b", "a//b", "../lock", "bad\x7fpath"):
                candidate = json.loads(json.dumps(valid)); candidate["workflow_lock_path"] = unsafe
                project = self._project(root, candidate)
                self.assertNotEqual(self._run_profile(project).returncode, 0, unsafe)

    def test_declaration_identity_exception_and_output_contracts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            valid = {"schema_version": 1, "workflow_lock_path": ".gpt-workflow.lock", "profile_id": "legacy-python-service", "exceptions": [{"id": "legacy-python-production-backend", "rule_id": "STACK-PYTHON-001", "reason": "Existing deployed service ✓", "scope": "Current backend", "approved_by": "owner", "migration_target": "rust-axum", "migration_required": False, "expires_at": None}]}
            project = self._project(root, valid)
            result = self._run_profile(project)
            self.assertIn("exception_ids=", result.stdout)
            self.assertIn("exception_rule_ids=", result.stdout)
            outside = root / "outside.json"
            outside.write_text(json.dumps(valid))
            outside_result = subprocess.run(["python3", str(ROOT / "scripts/validate-project-engineering-profile.py"), str(outside), "--project-root", str(project), "--planner-root", str(ROOT)], capture_output=True, text=True)
            self.assertNotEqual(outside_result.returncode, 0)
            for key, value in (("repository", "https://example.com/planner"), ("version", "latest"), ("document", "missing.md"), ("installed_at", "2026-07-25T00:00:00+03:00")):
                candidate = self._project(root, valid)
                lock = json.loads((candidate / ".gpt-workflow.lock").read_text()); lock[key] = value
                (candidate / ".gpt-workflow.lock").write_text(json.dumps(lock))
                self.assertNotEqual(self._run_profile(candidate).returncode, 0, key)
            non_applicable = json.loads(json.dumps(valid)); non_applicable["exceptions"][0]["rule_id"] = "STACK-FRONTEND-001"
            self.assertNotEqual(self._run_profile(self._project(root, non_applicable)).returncode, 0)
            bad_types = json.loads(json.dumps(valid)); bad_types["exceptions"][0]["migration_required"] = "no"
            self.assertNotEqual(self._run_profile(self._project(root, bad_types)).returncode, 0)
            self.assertNotEqual(self._run_profile(project, "--now", "2026-07-25T00:00:00+03:00").returncode, 0)

    def test_official_setup_lock_and_exact_commit_version(self) -> None:
        commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        declaration = {"schema_version": 1, "workflow_lock_path": ".gpt-workflow.lock", "profile_id": "python-tool", "exceptions": []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name, version in (("tagged", "v1.1.1"), ("exact", commit)):
                project = root / name
                project.mkdir()
                subprocess.run(["bash", str(ROOT / "setup.sh"), "--project", str(project), "--version", version, "--execution-mode", "repository_evidence", "--commit", commit], check=True, capture_output=True, text=True)
                lock = json.loads((project / ".gpt-workflow.lock").read_text())
                self.assertIn("installed_at", lock)
                self.assertNotIn("generated_at", lock)
                (project / "engineering-profile.json").write_text(json.dumps(declaration))
                integration = subprocess.run(["python3", str(ROOT / "scripts/validate-project-integration.py"), str(project)], capture_output=True, text=True)
                self.assertEqual(integration.returncode, 0, integration.stderr)
                result = self._run_profile(project)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_document_and_archive_contract_headings(self) -> None:
        required = ("Canonical use cases", "Forbidden/non-canonical uses", "Version/compatibility policy", "Ownership/dependency direction", "Testing", "Exceptions", "Review evidence")
        for path in (ROOT / "docs/engineering/languages").glob("*.md"):
            text = path.read_text()
            for heading in required:
                self.assertIn(f"### {heading}", text, str(path))
        for path in list((ROOT / "docs/engineering/frameworks").glob("*.md")) + list((ROOT / "docs/engineering/database").glob("*.md")):
            self.assertIn("## Operational review matrix", path.read_text(), str(path))
        prompt = (ROOT / "prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md").read_text()
        ordered_steps = [
            "1. Inspect source root", "3. If an existing source lock", "4. Create a temporary staging directory",
            "5. If an older valid lock differs", "8. Run `python3 \"$PLANNER_DIR/scripts/validate-project-integration.py\"`",
            "9. After lock reconciliation", "10. Generate `.gpt-review/archive-manifest.json`",
            "11. Run the dependency-free manifest validator", "12. Archive staging",
        ]
        positions = [prompt.index(step) for step in ordered_steps]
        self.assertEqual(positions, sorted(positions))
        self.assertGreater(prompt.index("validate-project-engineering-profile.py"), prompt.index("validate-project-integration.py"))

        profile_headings = ("Capabilities and rules", "Loaded documents and structure", "Template requirements", "Security, resources, testing, and operations", "Non-goals and exceptions", "Review procedure and artifacts")
        for path in (ROOT / "docs/engineering/profiles").glob("*.md"):
            text = path.read_text()
            for heading in profile_headings:
                self.assertIn(f"### {heading}", text, str(path))
        checklist_headings = ("Identity and structure", "Dependencies and correctness", "Errors, concurrency, and operations", "Security, database, and migrations", "Performance and configuration", "Tests, evidence, and classification", "Exceptions")
        for path in (ROOT / "docs/engineering/review-checklists").glob("*.md"):
            text = path.read_text()
            for heading in checklist_headings:
                self.assertIn(f"### {heading}", text, str(path))
        python_policy = (ROOT / "docs/engineering/languages/PYTHON.md").read_text()
        self.assertNotRegex(python_policy, r"\b(?:Django|Flask|FastAPI)\b")
        self.assertIn("automatic Rust rewrite", (ROOT / "docs/engineering/profiles/LEGACY_PYTHON_SERVICE.md").read_text())


if __name__ == "__main__":
    unittest.main()
