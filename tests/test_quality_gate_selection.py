from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "plan-quality-gates.py"
SCHEMA = ROOT / "schemas" / "quality-gate-execution-plan.schema.json"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PLANNER = load_module(SCRIPT, "quality_gate_plan")


def schema_accepts(value, schema, root=None):
    root = schema if root is None else root
    if "$ref" in schema:
        target = root
        for part in schema["$ref"][2:].split("/"):
            target = target[part]
        return schema_accepts(value, target, root)
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if "anyOf" in schema and not any(schema_accepts(value, child, root) for child in schema["anyOf"]):
        return False
    if "allOf" in schema and not all(schema_accepts(value, child, root) for child in schema["allOf"]):
        return False
    if "if" in schema and schema_accepts(value, schema["if"], root):
        if "then" in schema and not schema_accepts(value, schema["then"], root):
            return False
    if "type" in schema:
        types = schema["type"] if isinstance(schema["type"], list) else [schema["type"]]
        matches = []
        for kind in types:
            if kind == "object":
                matches.append(isinstance(value, dict))
            elif kind == "array":
                matches.append(isinstance(value, list))
            elif kind == "string":
                matches.append(isinstance(value, str))
            elif kind == "integer":
                matches.append(isinstance(value, int) and not isinstance(value, bool))
            elif kind == "boolean":
                matches.append(isinstance(value, bool))
            else:
                raise AssertionError(kind)
        if not any(matches):
            return False
    if isinstance(value, dict):
        if schema.get("additionalProperties") is False and set(value) - set(schema.get("properties", {})):
            return False
        if any(key not in value for key in schema.get("required", [])):
            return False
        return all(schema_accepts(value[key], child, root) for key, child in schema.get("properties", {}).items() if key in value)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", len(value)):
            return False
        if schema.get("uniqueItems") and len({json.dumps(item, sort_keys=True) for item in value}) != len(value):
            return False
        return all(schema_accepts(item, schema["items"], root) for item in value) if "items" in schema else True
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or len(value) > schema.get("maxLength", len(value)):
            return False
        import re

        return "pattern" not in schema or re.search(schema["pattern"], value) is not None
    if isinstance(value, int) and not isinstance(value, bool):
        return value >= schema.get("minimum", value) and value <= schema.get("maximum", value)
    return True


def git(repo: Path, *args: str, check: bool = True) -> str:
    result = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if check and result.returncode:
        raise AssertionError(f"git {args}: {result.stderr}")
    return result.stdout.strip()


class QualityGateSelectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name) / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.email", "test@example.invalid")
        git(self.repo, "config", "user.name", "Quality Gate Test")
        self.declaration = self._declaration()
        (self.repo / "quality-gates.json").write_text(json.dumps(self.declaration, indent=2) + "\n", encoding="utf-8")
        (self.repo / "src").mkdir()
        (self.repo / "docs").mkdir()
        (self.repo / "templates" / "project").mkdir(parents=True)
        (self.repo / ".gitignore").write_text("ignored.txt\n", encoding="utf-8")
        (self.repo / "src" / "a.py").write_text("print('a')\n", encoding="utf-8")
        (self.repo / "docs" / "readme.md").write_text("readme\n", encoding="utf-8")
        (self.repo / "templates" / "project" / "input.json").write_text("{}\n", encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.addCleanup(self.temp.cleanup)

    def _declaration(self):
        def command(identifier, file_args="none", mode="check"):
            return {
                "id": identifier,
                "argv": ["python3", "scripts/check.py"],
                "mode": mode,
                "file_args": file_args,
                "timeout_seconds": 60,
            }

        return {
            "schema_version": 1,
            "unmatched_changed_path": "reject",
            "cleanup": {"untracked_only": True, "paths": [".quality-gates/tmp/*"]},
            "generated": [
                {
                    "id": "generated-index",
                    "inputs": ["templates/project/*.json"],
                    "outputs": ["build/index.json"],
                    "argv": ["python3", "scripts/generate.py"],
                    "timeout_seconds": 60,
                }
            ],
            "rules": [
                {"id": "python", "paths": ["src/**/*.py"], "prepare": [command("python-each", "each")], "merge": [command("python-merge", "append")]},
                {"id": "docs", "paths": ["docs/**/*.md"], "prepare": [command("docs-check")], "merge": []},
                {"id": "templates", "paths": ["templates/project/*.json"], "prepare": [], "merge": [command("template-merge")]},
            ],
            "release": [command("release-suite")],
        }

    def run_plan(self, *, phase="prepare", target="WORKTREE", output=None, declaration="quality-gates.json", base=None):
        if output is None:
            output = Path(self.temp.name) / f"plan-{phase}-{target}.json"
        args = [
            "--repo", str(self.repo),
            "--declaration", declaration,
            "--base", base or self.base,
            "--phase", phase,
            "--target", target,
            "--output", str(output),
        ]
        result = subprocess.run(["python3", str(SCRIPT), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result, Path(output)

    def read_plan(self, path: Path):
        value = json.loads(path.read_text(encoding="utf-8"))
        PLANNER.validate_execution_plan(value)
        self.assertTrue(schema_accepts(value, self.schema))
        self.assertEqual(path.read_bytes()[-1:], b"\n")
        return value

    def snapshot(self):
        index = Path(git(self.repo, "rev-parse", "--git-path", "index"))
        if not index.is_absolute():
            index = self.repo / index
        return (
            git(self.repo, "rev-parse", "HEAD"),
            git(self.repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/tags"),
            index.read_bytes(),
            (self.repo / ".git" / "config").read_bytes(),
            git(self.repo, "status", "--porcelain=v1", "--untracked-files=all"),
            subprocess.run(["git", "-C", str(self.repo), "diff", "--binary"], stdout=subprocess.PIPE, check=True).stdout,
            subprocess.run(["git", "-C", str(self.repo), "diff", "--cached", "--binary"], stdout=subprocess.PIPE, check=True).stdout,
        )

    def test_worktree_success_is_read_only_and_expands_commands(self):
        (self.repo / "src" / "new.py").write_text("print('new')\n", encoding="utf-8")
        (self.repo / "src" / "a.py").write_text("print('changed')\n", encoding="utf-8")
        before = self.snapshot()
        result, output = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = self.read_plan(output)
        self.assertEqual(before, self.snapshot())
        self.assertEqual(plan["target"]["kind"], "worktree")
        self.assertEqual(plan["target"]["revision"], self.base)
        self.assertEqual(plan["changed"]["material_paths"], ["src/a.py", "src/new.py"])
        command = plan["selected_commands"][0]
        self.assertEqual(command["file_args"], "each")
        self.assertEqual(command["invocations"], [["python3", "scripts/check.py", "src/a.py"], ["python3", "scripts/check.py", "src/new.py"]])
        self.assertFalse(plan["cleanup"]["performed"])

    def test_committed_target_rename_and_generated_prepare_selection(self):
        git(self.repo, "mv", "src/a.py", "src/renamed.py")
        (self.repo / "templates" / "project" / "input.json").write_text('{"changed": true}\n', encoding="utf-8")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "rename")
        target = git(self.repo, "rev-parse", "HEAD")
        result, output = self.run_plan(target=target)
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = self.read_plan(output)
        self.assertEqual(plan["changed"]["material_paths"], ["src/a.py", "src/renamed.py", "templates/project/input.json"])
        rename = next(item for item in plan["changed"]["records"] if item["status"] == "R")
        self.assertEqual(rename, {"status": "R", "source": "src/a.py", "path": "src/renamed.py"})
        self.assertEqual(plan["selected_generated"][0]["matched_inputs"], ["templates/project/input.json"])
        self.assertEqual(plan["target"]["kind"], "commit")
        self.assertEqual(plan["target"]["revision"], target)
        self.assertEqual(plan["target"]["worktree_fingerprint"], "")

    def test_merge_omits_generated_actions_and_deduplicates_rule_commands(self):
        (self.repo / "src" / "a.py").write_text("changed\n", encoding="utf-8")
        git(self.repo, "add", "src/a.py")
        result, output = self.run_plan(phase="merge")
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = self.read_plan(output)
        self.assertEqual(plan["selected_generated"], [])
        self.assertEqual([item["id"] for item in plan["selected_commands"]], ["python-merge"])
        self.assertEqual(plan["selected_commands"][0]["invocations"], [["python3", "scripts/check.py", "src/a.py"]])

    def test_staged_deleted_untracked_and_ignored_paths_are_projected_safely(self):
        git(self.repo, "rm", "-q", "docs/readme.md")
        (self.repo / "ignored.txt").write_text("ignored\n", encoding="utf-8")
        (self.repo / "src" / "untracked.py").write_text("untracked\n", encoding="utf-8")
        result, output = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = self.read_plan(output)
        self.assertIn("docs/readme.md", plan["changed"]["material_paths"])
        self.assertIn("src/untracked.py", plan["changed"]["material_paths"])
        self.assertNotIn("ignored.txt", plan["changed"]["material_paths"])
        self.assertTrue(any(item["status"] == "D" for item in plan["changed"]["records"]))

    def test_glob_matcher_is_complete_case_sensitive_and_slash_safe(self):
        cases = {
            ("README.md", "README.md"): True,
            ("*.md", "README.md"): True,
            ("*.md", "docs/README.md"): False,
            ("docs/**/*.md", "docs/README.md"): True,
            ("docs/**/*.md", "docs/a/README.md"): True,
            ("docs/*.md", "docs/a/README.md"): False,
            ("src/[ab].py", "src/a.py"): True,
            ("src/[ab].py", "src/c.py"): False,
            ("src/*.PY", "src/a.py"): False,
            ("src/**", "src/a/b.py"): True,
            ("src/**", "srcx/a.py"): False,
        }
        for (pattern, path), expected in cases.items():
            self.assertEqual(PLANNER.match_repository_glob(pattern, path), expected, (pattern, path))

    def test_overlapping_rules_preserve_declaration_order_and_deduplicate_commands(self):
        command = {
            "id": "shared-check",
            "argv": ["python3", "scripts/check.py"],
            "mode": "check",
            "file_args": "append",
            "timeout_seconds": 60,
        }
        declaration = {
            "rules": [
                {"id": "first", "paths": ["src/*.py"], "prepare": [copy.deepcopy(command)]},
                {"id": "second", "paths": ["src/**/*.py"], "prepare": [copy.deepcopy(command)]},
            ],
            "generated": [],
        }
        selected = PLANNER._select(declaration, "prepare", ["src/a.py", "src/nested/b.py"])
        self.assertEqual(selected["selected_rule_ids"], ["first", "second"])
        self.assertEqual([item["id"] for item in selected["selected_commands"]], ["shared-check"])
        self.assertEqual(selected["selected_commands"][0]["matched_paths"], ["src/a.py", "src/nested/b.py"])

    def test_unmatched_paths_fail_closed_without_mutation(self):
        (self.repo / "unknown.txt").write_text("unknown\n", encoding="utf-8")
        before = self.snapshot()
        result, output = self.run_plan(output=Path(self.temp.name) / "failure.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unmatched changed paths", result.stderr)
        self.assertFalse(output.exists())
        self.assertEqual(before, self.snapshot())

    def test_identity_and_output_contracts_fail_closed(self):
        outside = Path(self.temp.name) / "outside.json"
        inside = self.repo / "inside.json"
        result, _ = self.run_plan(output=inside)
        self.assertNotEqual(result.returncode, 0)
        result, _ = self.run_plan(base="0" * 40, output=outside)
        self.assertNotEqual(result.returncode, 0)
        result, _ = self.run_plan(output=outside)
        self.assertEqual(result.returncode, 0, result.stderr)
        result, _ = self.run_plan(output=outside)
        self.assertNotEqual(result.returncode, 0)

    def test_output_is_byte_deterministic_and_declaration_hash_is_exact(self):
        first = Path(self.temp.name) / "first.json"
        second = Path(self.temp.name) / "second.json"
        (self.repo / "src" / "a.py").write_text("same\n", encoding="utf-8")
        result, _ = self.run_plan(output=first)
        self.assertEqual(result.returncode, 0, result.stderr)
        result, _ = self.run_plan(output=second)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(first.read_bytes(), second.read_bytes())
        plan = self.read_plan(first)
        import hashlib

        self.assertEqual(plan["declaration"]["sha256"], hashlib.sha256((self.repo / "quality-gates.json").read_bytes()).hexdigest())

    def test_generated_outputs_preserve_declaration_order_byte_stably(self):
        declaration = copy.deepcopy(self.declaration)
        declaration["generated"][0]["outputs"] = ["build/z.json", "build/a.json"]
        declaration["rules"][1]["paths"].append("quality-gates.json")
        (self.repo / "quality-gates.json").write_text(json.dumps(declaration, indent=2) + "\n", encoding="utf-8")
        (self.repo / "templates/project/input.json").write_text('{"changed": true}\n', encoding="utf-8")
        first = Path(self.temp.name) / "ordered-first.json"
        second = Path(self.temp.name) / "ordered-second.json"
        result, _ = self.run_plan(output=first)
        self.assertEqual(result.returncode, 0, result.stderr)
        result, _ = self.run_plan(output=second)
        self.assertEqual(result.returncode, 0, result.stderr)
        first_plan = self.read_plan(first)
        second_plan = self.read_plan(second)
        self.assertEqual(first_plan["selected_generated"][0]["outputs"], ["build/z.json", "build/a.json"])
        self.assertEqual(first_plan["selected_generated"][0]["matched_inputs"], ["templates/project/input.json"])
        self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_phase_target_and_timeout_invariants_match_schema(self):
        (self.repo / "src" / "a.py").write_text("changed\n", encoding="utf-8")
        result, output = self.run_plan()
        self.assertEqual(result.returncode, 0, result.stderr)
        valid = self.read_plan(output)

        merge_fix = copy.deepcopy(valid)
        merge_fix["phase"] = "merge"
        merge_fix["selected_generated"] = []
        merge_fix["counts"]["selected_generated"] = 0
        merge_fix["selected_commands"][0]["mode"] = "fix"
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(merge_fix)
        self.assertFalse(schema_accepts(merge_fix, self.schema))

        merge_generated = copy.deepcopy(valid)
        merge_generated["phase"] = "merge"
        merge_generated["counts"]["selected_generated"] = len(merge_generated["selected_generated"])
        merge_generated["selected_generated"] = [{
            "id": "generated-index",
            "matched_inputs": ["src/a.py"],
            "outputs": ["build/index.json"],
            "argv": ["python3", "scripts/generate.py"],
            "timeout_seconds": 60,
        }]
        merge_generated["counts"]["selected_generated"] = 1
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(merge_generated)
        self.assertFalse(schema_accepts(merge_generated, self.schema))

        worktree_bad_fingerprint = copy.deepcopy(valid)
        worktree_bad_fingerprint["target"]["worktree_fingerprint"] = ""
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(worktree_bad_fingerprint)
        self.assertFalse(schema_accepts(worktree_bad_fingerprint, self.schema))

        commit_bad_projection = copy.deepcopy(valid)
        commit_bad_projection["target"] = {
            "kind": "commit",
            "revision": self.base,
            "head_revision": self.base,
            "worktree_fingerprint": "f" * 64,
            "status_projection": [" M src/a.py"],
        }
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(commit_bad_projection)
        self.assertFalse(schema_accepts(commit_bad_projection, self.schema))

        generated_timeout = copy.deepcopy(valid)
        generated_timeout["selected_generated"] = [{
            "id": "generated-index",
            "matched_inputs": ["src/a.py"],
            "outputs": ["build/index.json"],
            "argv": ["python3", "scripts/generate.py"],
            "timeout_seconds": 3601,
        }]
        generated_timeout["counts"]["selected_generated"] = 1
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(generated_timeout)
        self.assertFalse(schema_accepts(generated_timeout, self.schema))

        command_timeout = copy.deepcopy(valid)
        command_timeout["selected_commands"][0]["timeout_seconds"] = 3601
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(command_timeout)
        self.assertFalse(schema_accepts(command_timeout, self.schema))

        empty_rule_paths = copy.deepcopy(valid)
        empty_rule_paths["selected_rules"][0]["matched_paths"] = []
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(empty_rule_paths)
        self.assertFalse(schema_accepts(empty_rule_paths, self.schema))

    def test_declaration_hash_and_validation_use_one_byte_snapshot(self):
        original = (self.repo / "quality-gates.json").read_bytes()
        validator = PLANNER._quality_validator()
        proxy = mock.Mock(wraps=validator)
        proxy.load_json = mock.Mock(side_effect=AssertionError("declaration was re-read"))
        with mock.patch.object(PLANNER, "_quality_validator", return_value=proxy):
            plan = PLANNER.build_plan(str(self.repo), "quality-gates.json", self.base, "prepare", "WORKTREE")
        import hashlib

        self.assertEqual(plan["declaration"]["sha256"], hashlib.sha256(original).hexdigest())
        proxy.load_json.assert_not_called()
        self.assertEqual((self.repo / "quality-gates.json").read_bytes(), original)

    def test_worktree_change_during_selection_fails_closed_without_output(self):
        (self.repo / "src" / "a.py").write_text("changed\n", encoding="utf-8")
        output = Path(self.temp.name) / "unstable.json"
        before = self.snapshot()
        original_select = PLANNER._select

        def mutate_after_collection(declaration, phase, material_paths):
            selected = original_select(declaration, phase, material_paths)
            (self.repo / "src" / "a.py").write_text("changed during selection\n", encoding="utf-8")
            return selected

        with mock.patch.object(PLANNER, "_select", side_effect=mutate_after_collection):
            with self.assertRaises(PLANNER.QualityGatePlanError):
                PLANNER.build_plan(str(self.repo), "quality-gates.json", self.base, "prepare", "WORKTREE")
        self.assertFalse(output.exists())
        (self.repo / "src" / "a.py").write_text("changed\n", encoding="utf-8")
        self.assertEqual(before, self.snapshot())

    def test_invalid_utf8_path_and_conflicted_index_are_rejected(self):
        bad = os.fsencode(str(self.repo)) + b"/bad-\xff.txt"
        descriptor = os.open(bad, os.O_WRONLY | os.O_CREAT, 0o644)
        os.close(descriptor)
        result, _ = self.run_plan(output=Path(self.temp.name) / "bad-path.json")
        self.assertNotEqual(result.returncode, 0)
        os.unlink(bad)
        git(self.repo, "checkout", "-qb", "conflict")
        (self.repo / "src" / "a.py").write_text("branch\n", encoding="utf-8")
        git(self.repo, "commit", "-qam", "branch")
        git(self.repo, "checkout", "-q", "-")
        (self.repo / "src" / "a.py").write_text("main\n", encoding="utf-8")
        git(self.repo, "commit", "-qam", "main")
        merge = subprocess.run(["git", "-C", str(self.repo), "merge", "conflict"], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(merge.returncode, 0)
        result, _ = self.run_plan(output=Path(self.temp.name) / "conflict.json")
        self.assertNotEqual(result.returncode, 0)

    def test_copy_status_is_rejected_and_symlink_declaration_is_rejected(self):
        (self.repo / "src" / "copy.py").write_bytes((self.repo / "src" / "a.py").read_bytes())
        git(self.repo, "add", "src/copy.py")
        git(self.repo, "commit", "-qm", "copy")
        result, _ = self.run_plan(target=git(self.repo, "rev-parse", "HEAD"), output=Path(self.temp.name) / "copy.json")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("copy status", result.stderr)
        link = self.repo / "quality-gates-link.json"
        link.symlink_to(self.repo / "quality-gates.json")
        result, _ = self.run_plan(declaration="quality-gates-link.json", output=Path(self.temp.name) / "link.json")
        self.assertNotEqual(result.returncode, 0)

    def test_schema_and_model_reject_unknown_fields(self):
        value = {
            "schema_version": 1,
            "phase": "prepare",
            "declaration": {"path": "quality-gates.json", "sha256": "0" * 64},
            "base_revision": self.base,
            "target": {"kind": "commit", "revision": self.base, "head_revision": self.base, "worktree_fingerprint": "", "status_projection": []},
            "changed": {"records": [], "material_paths": []},
            "selected_rules": [],
            "selected_rule_ids": [],
            "selected_generated": [],
            "cleanup": {"untracked_only": True, "paths": [], "performed": False},
            "selected_commands": [],
            "counts": {"changed_records": 0, "material_paths": 0, "selected_rules": 0, "selected_generated": 0, "selected_commands": 0, "invocations": 0},
        }
        PLANNER.validate_execution_plan(value)
        self.assertTrue(schema_accepts(value, self.schema))
        invalid = copy.deepcopy(value)
        invalid["unknown"] = True
        with self.assertRaises(PLANNER.QualityGatePlanError):
            PLANNER.validate_execution_plan(invalid)
        self.assertFalse(schema_accepts(invalid, self.schema))


if __name__ == "__main__":
    unittest.main()
