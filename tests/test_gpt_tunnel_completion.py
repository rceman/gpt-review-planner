from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def load_validator():
    spec = importlib.util.spec_from_file_location("completion_validator", ROOT / "scripts/validate-gpt-tunnel-completion.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CompletionContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = load_validator()

    def base(self, status="succeeded"):
        return {
            "schema_version": 1,
            "run_id": "01234567-89ab-cdef-0123-456789abcdef",
            "task_sha256": "a" * 64,
            "status": status,
            "summary": "completed",
            "gate_results": [{"id": "G1", "exit_code": 0}, {"id": "G2", "exit_code": 0}],
            "acceptance_coverage": ["AC1", "AC2"],
            "deviations": [],
            "remaining_risks": [],
        }

    def valid(self, value, **kwargs):
        self.assertEqual(self.validator.validate_value(value, expected_run_id="01234567-89ab-cdef-0123-456789abcdef", expected_task_sha256="a" * 64, gate_count=2, acceptance_count=2, **kwargs), [])

    def test_exact_success_is_ordered_and_compact(self):
        self.valid(self.base())

    def test_success_requires_all_zero_gates(self):
        value = self.base(); value["gate_results"][1]["exit_code"] = 1
        self.assertTrue(self.validator.validate_value(value, expected_run_id="01234567-89ab-cdef-0123-456789abcdef", expected_task_sha256="a" * 64, gate_count=2, acceptance_count=2))

    def test_non_success_accepts_only_executed_prefix_and_ordered_subset(self):
        value = self.base("failed"); value["gate_results"] = [{"id": "G1", "exit_code": 1}]; value["acceptance_coverage"] = ["AC1"]
        self.valid(value)
        value["gate_results"] = [{"id": "G2", "exit_code": 1}]
        self.assertTrue(self.validator.validate_value(value, expected_run_id="01234567-89ab-cdef-0123-456789abcdef", expected_task_sha256="a" * 64, gate_count=2, acceptance_count=2))

    def test_unknown_duplicate_and_forbidden_fields_rejected(self):
        value = self.base(); value["task_id"] = "forbidden"
        self.assertTrue(self.validator.validate_value(value, expected_run_id="run-001", expected_task_sha256="a" * 64, gate_count=2, acceptance_count=2))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "completion.json"
            path.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
            with self.assertRaises(self.validator.DuplicateKey):
                self.validator.load_json(path)

    def test_explicit_identity_and_count_arguments_are_authoritative(self):
        value = self.base()
        self.assertTrue(self.validator.validate_value(value, expected_run_id="different", expected_task_sha256="a" * 64, gate_count=2, acceptance_count=2))
        self.assertTrue(self.validator.validate_value(value, expected_run_id="01234567-89ab-cdef-0123-456789abcdef", expected_task_sha256="b" * 64, gate_count=2, acceptance_count=2))

    def test_schema_has_only_the_completion_fields(self):
        schema = json.loads((ROOT / "schemas/gpt-tunnel-completion.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(set(schema["properties"]), {"schema_version", "run_id", "task_sha256", "status", "summary", "gate_results", "acceptance_coverage", "deviations", "remaining_risks"})
        self.assertNotIn("project_id", schema["properties"])
        self.assertNotIn("task_id", schema["properties"])

    def test_run_id_is_canonical_uuid_and_exit_code_is_unbounded_integer(self):
        value = self.base("failed")
        value["gate_results"][0]["exit_code"] = -9001
        self.assertEqual(
            self.validator.validate_value(
                value,
                expected_run_id="01234567-89ab-cdef-0123-456789abcdef",
                expected_task_sha256="a" * 64,
                gate_count=2,
                acceptance_count=2,
            ),
            [],
        )
        value["run_id"] = "run-001"
        self.assertTrue(self.validator.validate_value(value, gate_count=2, acceptance_count=2))

    def test_malformed_acceptance_values_return_errors_without_throwing(self):
        value = self.base("failed")
        value["gate_results"] = []
        value["acceptance_coverage"] = [None, {"id": "AC1"}, "AC2"]
        errors = self.validator.validate_value(value, gate_count=2, acceptance_count=2)
        self.assertTrue(errors)


if __name__ == "__main__":
    unittest.main()
