from __future__ import annotations

import copy
import importlib.util
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "schemas/project-identifiers.schema.json"
VALIDATOR_PATH = ROOT / "scripts/validate-project-identifiers.py"
FIXTURES = (
    ROOT / "fixtures/project-identifiers/gpt-review-planner.json",
    ROOT / "fixtures/project-identifiers/gpt-tunnel-gateway.json",
)


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_project_identifiers", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


validator = load_validator()
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def load_fixture(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def json_schema_equal(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    return type(left) is type(right) and left == right


def schema_accepts(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    if set(value) != set(SCHEMA["required"]):
        return False
    properties = SCHEMA["properties"]
    for key, rule in properties.items():
        candidate = value[key]
        if "const" in rule and not json_schema_equal(candidate, rule["const"]):
            return False
        expected_type = rule.get("type")
        if expected_type == "string":
            if not isinstance(candidate, str):
                return False
            if len(candidate) < rule.get("minLength", 0) or len(candidate) > rule.get("maxLength", math.inf):
                return False
            if re.fullmatch(rule["pattern"], candidate) is None:
                return False
        elif expected_type == "integer":
            if isinstance(candidate, bool) or not isinstance(candidate, (int, float)):
                return False
            if isinstance(candidate, float) and not math.isfinite(candidate):
                return False
            if (
                candidate != math.floor(candidate)
                or candidate < rule["minimum"]
                or candidate > rule["maximum"]
            ):
                return False
    return True


class ProjectIdentifierTests(unittest.TestCase):
    def assert_valid(self, value: dict[str, Any], **kwargs: Any) -> None:
        validator.validate_project_identifiers(value, **kwargs)
        self.assertTrue(schema_accepts(value))

    def assert_invalid(self, value: dict[str, Any]) -> None:
        with self.assertRaises(validator.ProjectIdentifiersError):
            validator.validate_project_identifiers(value)
        self.assertFalse(schema_accepts(value))

    def test_fixtures_validate_and_have_exact_assignments(self):
        expected = {
            "gpt-review-planner": "GRP",
            "gpt-tunnel-gateway": "GTW",
        }
        for path in FIXTURES:
            with self.subTest(path=path):
                value = load_fixture(path)
                self.assertEqual(value["project_code"], expected[value["project_id"]])
                self.assert_valid(value)
                result = subprocess.run(
                    [sys.executable, str(VALIDATOR_PATH), str(path)],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_schema_validator_parity_for_record_failures(self):
        cases: list[tuple[str, dict[str, Any]]] = []
        missing = load_fixture(FIXTURES[0])
        del missing["project_code"]
        cases.append(("missing field", missing))
        unknown = load_fixture(FIXTURES[0])
        unknown["extra"] = True
        cases.append(("unknown field", unknown))
        for candidate in (True, "1", 0, 1.5, 2):
            value = load_fixture(FIXTURES[0])
            value["schema_version"] = candidate
            cases.append((f"schema_version {candidate!r}", value))
        for candidate in ("GPT-review-planner", "-planner", "", "gpt/review", "gpt review"):
            value = load_fixture(FIXTURES[0])
            value["project_id"] = candidate
            cases.append((f"project_id {candidate!r}", value))
        for candidate in ("grp", "GRP1", "GR", "GRP "):
            value = load_fixture(FIXTURES[0])
            value["project_code"] = candidate
            cases.append((f"project_code {candidate!r}", value))
        for field in ("next_task_number", "next_adr_number"):
            for candidate in (
                0,
                -1,
                True,
                0.5,
                float("nan"),
                float("inf"),
                float("-inf"),
                9007199254740992,
                9007199254740992.0,
            ):
                value = load_fixture(FIXTURES[0])
                value[field] = candidate
                cases.append((f"{field} {candidate!r}", value))
        for name, value in cases:
            with self.subTest(name=name):
                self.assert_invalid(value)

        for project_id in ("1planner", "planner_name", "planner-name", "planner_"):
            value = load_fixture(FIXTURES[0])
            value["project_id"] = project_id
            with self.subTest(project_id=project_id):
                self.assert_valid(value)

    def test_schema_version_one_point_zero_and_integral_counters_follow_json_rules(self):
        value = load_fixture(FIXTURES[0])
        value["schema_version"] = 1.0
        value["next_task_number"] = 2.0
        value["next_adr_number"] = 3.0
        self.assert_valid(value)

    def test_exact_cross_language_maximum_is_shared_by_records_and_ids(self):
        maximum = 9007199254740991
        value = load_fixture(FIXTURES[0])
        value["next_task_number"] = float(maximum)
        value["next_adr_number"] = float(maximum)
        self.assert_valid(value)
        self.assertEqual(validator.parse_task_id(f"GRP-TSK{maximum}", "GRP")["number"], maximum)
        self.assertEqual(validator.parse_run_id(f"GRP-TSK1-RUN{maximum}", "GRP")["run_number"], maximum)
        self.assertEqual(validator.parse_adr_id(f"GRP-ADR{maximum}", "GRP")["number"], maximum)
        for identifier, parser in (
            (f"GRP-TSK{maximum + 1}", validator.parse_task_id),
            (f"GRP-TSK1-RUN{maximum + 1}", validator.parse_run_id),
            (f"GRP-ADR{maximum + 1}", validator.parse_adr_id),
        ):
            with self.subTest(identifier=identifier):
                with self.assertRaises(validator.ProjectIdentifiersError):
                    parser(identifier, "GRP")

    def test_duplicate_keys_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            duplicate = root / "duplicate.json"
            duplicate.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaisesRegex(validator.ProjectIdentifiersError, "duplicate JSON key"):
                validator.load_json(duplicate)
            real = root / "real.json"
            link = root / "link.json"
            real.write_bytes(FIXTURES[0].read_bytes())
            os.symlink(real, link)
            with self.assertRaisesRegex(validator.ProjectIdentifiersError, "symlink"):
                validator.load_json(link)

    def test_canonical_task_run_adr_ids_and_code_binding(self):
        self.assertEqual(validator.parse_task_id("GRP-TSK1", "GRP")["number"], 1)
        self.assertEqual(validator.parse_run_id("GRP-TSK1-RUN27", "GRP")["run_number"], 27)
        self.assertEqual(validator.parse_adr_id("GRP-ADR3", "GRP")["number"], 3)
        self.assertEqual(
            validator.task_branch_name("GRP-TSK1", "compact-identifiers", "GRP"),
            "task/GRP-TSK1-compact-identifiers",
        )
        for identifier, parser in (
            ("GRP-T1", validator.parse_task_id),
            ("GRP-T1-R1", validator.parse_run_id),
            ("GRP-A1", validator.parse_adr_id),
            ("GRP-TSK01", validator.parse_task_id),
            ("GRP-TSK1-RUN01", validator.parse_run_id),
            ("GRP-ADR01", validator.parse_adr_id),
            ("GTW-TSK1", validator.parse_task_id),
            ("GRP_TSK1", validator.parse_task_id),
            ("GRP-TSK", validator.parse_task_id),
            ("GRP-TSK1-RUN", validator.parse_run_id),
            ("GRP-ADR", validator.parse_adr_id),
            ("01234567-89ab-cdef-0123-456789abcdef", validator.parse_task_id),
        ):
            with self.subTest(identifier=identifier):
                with self.assertRaises(validator.ProjectIdentifiersError):
                    parser(identifier, "GRP")
        for task_id, slug in (
            ("GRP-T1", "compact-identifiers"),
            ("GRP-TSK1", "Compact-identifiers"),
            ("GRP-TSK1", "compact_identifiers"),
        ):
            with self.subTest(task_id=task_id, slug=slug):
                with self.assertRaises(validator.ProjectIdentifiersError):
                    validator.task_branch_name(task_id, slug, "GRP")

    def test_project_code_and_identifiers_are_immutable_bindings(self):
        record = load_fixture(FIXTURES[0])
        self.assert_valid(record, expected_project_id="gpt-review-planner", expected_project_code="GRP")
        with self.assertRaises(validator.ProjectIdentifiersError):
            validator.validate_project_identifiers(record, expected_project_code="GTW")
        with self.assertRaises(validator.ProjectIdentifiersError):
            validator.parse_task_id("GTW-TSK1", "GRP")

    def test_documentation_states_all_allocation_and_cutover_rules(self):
        documentation = (ROOT / "docs/DURABLE_IDENTIFIERS.md").read_text(encoding="utf-8")
        text = " ".join(documentation.split())
        for phrase in (
            "atomic read-lock-validate-increment-write transaction",
            "do not scan history",
            "compute a maximum",
            "never reused",
            "run numbering is local to its task",
            "task/<TASK-ID>-<slug>",
            "replaces",
            "supersedes",
            "remains readable as long as that history exists",
            "UUID creation",
            "mutation aliases",
            "dual operational paths",
            "fuzzy lookup",
            "task: <CODE>-TSK<N>",
            "run: <TASK-ID>-RUN<N>",
            "ADR: <CODE>-ADR<N>",
            "pre-activation single-letter-token records",
        ):
            self.assertIn(phrase, text)
        self.assertNotIn("task: <CODE>-T<N>", documentation)
        self.assertNotIn("run: <TASK-ID>-R<N>", documentation)
        self.assertNotIn("ADR: <CODE>-A<N>", documentation)

    def test_bounded_identifier_surfaces_declare_only_new_operational_tokens(self):
        validator_source = VALIDATOR_PATH.read_text(encoding="utf-8")
        self.assertIn("-TSK(?P<number>", validator_source)
        self.assertIn("-RUN(?P<number>", validator_source)
        self.assertIn("-ADR(?P<number>", validator_source)
        self.assertNotIn("TASK_RE = re.compile(r\"^(?P<code>[A-Z]{3})-T(?P<number>", validator_source)
        self.assertNotIn("RUN_RE = re.compile(r\"^(?P<task>[A-Z]{3}-T[1-9][0-9]*)-R", validator_source)
        self.assertNotIn("ADR_RE = re.compile(r\"^(?P<code>[A-Z]{3})-A(?P<number>", validator_source)


if __name__ == "__main__":
    unittest.main()
