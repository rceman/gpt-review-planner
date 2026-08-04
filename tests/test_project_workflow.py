from __future__ import annotations

import copy
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/project-workflow.schema.json"
TEMPLATE_PATH = ROOT / "templates/project/project-workflow.json"
PLANNER_FIXTURE = ROOT / "fixtures/project-workflow/gpt-review-planner/project-workflow.json"
GATEWAY_FIXTURE = ROOT / "fixtures/project-workflow/gpt-tunnel-gateway/project-workflow.json"
VALIDATOR_PATH = ROOT / "scripts/validate-project-workflow.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_project_workflow", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()


def canonical_value() -> dict[str, Any]:
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def resolve_schema(node: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    reference = node.get("$ref")
    if reference is None:
        return node
    prefix = "#/$defs/"
    assert reference.startswith(prefix)
    return schema["$defs"][reference.removeprefix(prefix)]


def schema_accepts(value: Any, node: dict[str, Any] | None = None) -> bool:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return _schema_accepts(value, node or schema, schema)


def _schema_accepts(value: Any, node: dict[str, Any], root_schema: dict[str, Any]) -> bool:
    node = resolve_schema(node, root_schema)
    if "const" in node and value != node["const"]:
        return False
    if "enum" in node and value not in node["enum"]:
        return False
    expected_type = node.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            return False
        if node.get("additionalProperties") is False and set(value) - set(node.get("properties", {})):
            return False
        if any(key not in value for key in node.get("required", [])):
            return False
        return all(
            _schema_accepts(value[key], child, root_schema)
            for key, child in node.get("properties", {}).items()
            if key in value
        )
    if expected_type == "string" and not isinstance(value, str):
        return False
    if expected_type == "integer" and (isinstance(value, bool) or not isinstance(value, int)):
        return False
    if expected_type == "boolean" and not isinstance(value, bool):
        return False
    if "pattern" in node and isinstance(value, str):
        import re

        if re.fullmatch(node["pattern"], value) is None:
            return False
    return True


class ProjectWorkflowTests(unittest.TestCase):
    def assert_valid(self, value: dict[str, Any]) -> None:
        validator.validate(value)
        self.assertTrue(schema_accepts(value))

    def assert_invalid(self, value: dict[str, Any]) -> None:
        with self.assertRaises(validator.ProjectWorkflowError):
            validator.validate(value)
        self.assertFalse(schema_accepts(value))

    def test_canonical_template_and_fixtures_are_valid_and_byte_identical(self):
        template = TEMPLATE_PATH.read_bytes()
        self.assertEqual(template, PLANNER_FIXTURE.read_bytes())
        self.assertEqual(template, GATEWAY_FIXTURE.read_bytes())
        for path in (TEMPLATE_PATH, PLANNER_FIXTURE, GATEWAY_FIXTURE):
            with self.subTest(path=path):
                value = json.loads(path.read_text(encoding="utf-8"))
                self.assert_valid(value)
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR_PATH), str(path)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_schema_and_validator_parity_for_contract_matrix(self):
        cases: list[tuple[str, dict[str, Any]]] = []

        missing = canonical_value()
        del missing["ci"]
        cases.append(("missing top-level field", missing))

        unknown = canonical_value()
        unknown["unexpected"] = True
        cases.append(("unknown top-level field", unknown))

        nested_unknown = canonical_value()
        nested_unknown["branching"]["unexpected"] = True
        cases.append(("unknown nested field", nested_unknown))

        for field, value in (
            ("default_branch", "trunk"),
            ("integration_branch", "release"),
            ("task_branch_prefix", "tasks/"),
            ("one_active_task", False),
            ("release_admission", "direct_to_main"),
            ("stale_task_policy", "rebase_in_place"),
            ("revision_suffix", "-{revision}"),
        ):
            candidate = canonical_value()
            candidate["branching"][field] = value
            cases.append((f"branching.{field}", candidate))

        for field, value in (
            ("completion_boundary", "local_commit"),
            ("wait_for_ci", True),
            ("owns_merge", True),
            ("owns_release", True),
            ("owns_history_rewrite", True),
        ):
            candidate = canonical_value()
            candidate["agent"][field] = value
            cases.append((f"agent.{field}", candidate))

        for field, value in (
            ("task", "required"),
            ("task_merge", "always"),
            ("release", "later"),
        ):
            candidate = canonical_value()
            candidate["ci"][field] = value
            cases.append((f"ci.{field}", candidate))

        for value in ("/quality-gates.json", "../quality-gates.json", r"quality\gates.json"):
            candidate = canonical_value()
            candidate["quality"]["contract_path"] = value
            cases.append((f"path {value}", candidate))

        candidate = canonical_value()
        candidate["quality"]["prepare_commit_required"] = False
        cases.append(("prepare commit not required", candidate))

        for name, candidate in cases:
            with self.subTest(name=name):
                self.assert_invalid(candidate)

    def test_duplicate_json_keys_are_rejected(self):
        duplicate = '{"schema_version":1,"schema_version":1}'
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project-workflow.json"
            path.write_text(duplicate, encoding="utf-8")
            with self.assertRaisesRegex(validator.ProjectWorkflowError, "duplicate JSON key"):
                validator.load_json(path)
            result = subprocess.run(
                [sys.executable, str(VALIDATOR_PATH), str(path)],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("duplicate JSON key", result.stderr)

    def test_malformed_json_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "project-workflow.json"
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaises(validator.ProjectWorkflowError):
                validator.load_json(path)

    def test_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "real.json"
            link = root / "project-workflow.json"
            target.write_bytes(TEMPLATE_PATH.read_bytes())
            os.symlink(target, link)
            with self.assertRaisesRegex(validator.ProjectWorkflowError, "symlink"):
                validator.load_json(link)

    def test_validator_accepts_only_the_canonical_contract_shape(self):
        value = canonical_value()
        self.assertEqual(
            set(value),
            {"schema_version", "branching", "agent", "ci", "quality"},
        )
        self.assertEqual(value["branching"], {
            "default_branch": "main",
            "integration_branch": "develop",
            "task_branch_prefix": "task/",
            "one_active_task": True,
            "release_admission": "merge_into_integration",
            "stale_task_policy": "new_revision_branch",
            "revision_suffix": "-r{revision}",
        })
        self.assertEqual(value["agent"], {
            "completion_boundary": "pushed_task_commit",
            "wait_for_ci": False,
            "owns_merge": False,
            "owns_release": False,
            "owns_history_rewrite": False,
        })
        self.assert_valid(value)


if __name__ == "__main__":
    unittest.main()
