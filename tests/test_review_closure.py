from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate-review-closure.py"
CONTRACT = ROOT / "profiles/review-closure.json"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_review_closure", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReviewClosureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.validator = load_validator()
        cls.valid = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def assert_invalid(self, data: object) -> None:
        with self.assertRaises(self.validator.ContractError):
            self.validator.validate_contract(data)

    def test_current_contract_and_cli_pass(self) -> None:
        counts = self.validator.validate_contract(self.valid)
        self.assertEqual(counts["queues"], 3)
        result = subprocess.run(
            ["python3", str(SCRIPT), str(CONTRACT)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PASS: bounded review closure contract", result.stdout)

    def test_unknown_missing_duplicate_and_control_values_fail(self) -> None:
        unknown = copy.deepcopy(self.valid)
        unknown["invented"] = True
        self.assert_invalid(unknown)

        missing = copy.deepcopy(self.valid)
        del missing["stop_rule"]
        self.assert_invalid(missing)

        duplicate = copy.deepcopy(self.valid)
        duplicate["blocker_bases"].append(duplicate["blocker_bases"][0])
        self.assert_invalid(duplicate)

        control = copy.deepcopy(self.valid)
        control["reopen_bases"][0] += "\x7f"
        self.assert_invalid(control)

    def test_policy_weakening_fails(self) -> None:
        mutations = []
        wrong_mode = copy.deepcopy(self.valid)
        wrong_mode["post_implementation_review_mode"] = "full"
        mutations.append(wrong_mode)

        unlimited = copy.deepcopy(self.valid)
        unlimited["max_normal_correction_rounds"] = 9
        mutations.append(unlimited)

        missing_blocker = copy.deepcopy(self.valid)
        missing_blocker["blocker_bases"].remove("required_gate_failure")
        mutations.append(missing_blocker)

        stronger_is_blocker = copy.deepcopy(self.valid)
        stronger_is_blocker["non_blocking_classes"].remove("stronger_unapproved_contract")
        mutations.append(stronger_is_blocker)

        no_stop = copy.deepcopy(self.valid)
        no_stop["stop_rule"]["stop_after_verdict"] = False
        mutations.append(no_stop)

        for mutation in mutations:
            with self.subTest(mutation=mutation):
                self.assert_invalid(mutation)

    def test_machine_schema_and_contract_agree_on_top_level_fields(self) -> None:
        schema = json.loads((ROOT / "schemas/review-closure.schema.json").read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(set(schema["required"]), set(self.validator.EXPECTED_KEYS))
        self.assertEqual(set(schema["properties"]), set(self.validator.EXPECTED_KEYS))


class ReviewClosureIntegrationTests(unittest.TestCase):
    def text(self, path: str) -> str:
        return (ROOT / path).read_text(encoding="utf-8")

    def test_root_workflow_and_readme_load_protocol(self) -> None:
        for path in ("README.md", "GPT_REVIEW_PLANNER.md"):
            text = self.text(path)
            self.assertIn("REVIEW_CLOSURE_PROTOCOL.md", text)
            self.assertIn("validate-review-closure.py", text)

    def test_review_and_implement_prompt_locks_scope_and_uses_delta_review(self) -> None:
        text = self.text("prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md")
        for phrase in (
            "acceptance contract",
            "scope lock",
            "review_mode=delta",
            "MERGE_BLOCKERS",
            "FOLLOW_UP_BACKLOG",
            "OBSERVATIONS",
            "MERGE_READY",
            "stronger contract",
        ):
            self.assertIn(phrase, text)
        self.assertIn("After declaring `MERGE_READY`", text)
        self.assertIn("required merge-oriented `AGENT_HANDOFF`", text)

    def test_review_only_prompt_separates_blockers_from_backlog(self) -> None:
        text = self.text("prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md")
        self.assertIn("MERGE_BLOCKERS", text)
        self.assertIn("FOLLOW_UP_BACKLOG", text)
        self.assertIn("OBSERVATIONS", text)
        self.assertIn("does not authorize implementation", text)

    def test_patch_pack_prompt_preserves_approved_acceptance_scope(self) -> None:
        text = self.text("prompts/GPT_CREATE_PATCH_PACK.md")
        self.assertIn("GPT authors architecture", text)
        self.assertIn("approved scope is locked", text)
        self.assertIn("static validation", text)
        self.assertIn("unauthorized shims", text)

    def test_archive_guide_documents_normal_round_budget(self) -> None:
        text = self.text("docs/PROJECT_ARCHIVE_REVIEW.md")
        self.assertIn("one normal correction round", text)
        self.assertIn("full reopen", text)
        self.assertIn("MERGE_READY", text)


if __name__ == "__main__":
    unittest.main()
