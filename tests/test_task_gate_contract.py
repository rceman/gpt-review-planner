from __future__ import annotations

import copy
import json
import shlex
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.task_gate_contract import (
    TaskGateContractError,
    contract_identity,
    gate_plan,
    manifest_gates,
    validate_contract,
    validate_gate_run_identity,
    validate_generated_outputs,
)


ROOT = Path(__file__).resolve().parents[1]


class TaskGateContractTests(unittest.TestCase):
    def contract(self):
        commands = [
            ("G1", "Focused task-gate contract tests", ["python3", "-m", "unittest", "tests.test_task_gate_contract", "-v"], "unittest", "focused_count"),
            ("G2", "Repository unit tests", ["python3", "-m", "unittest", "discover", "-s", "tests", "-v"], "unittest", "unit_count"),
            ("G3", "Pytest suite", ["python3", "-m", "pytest", "-q"], "pytest", "pytest_count"),
            ("G4", "Python compilation", ["python3", "-m", "compileall", "-q", "scripts", "tests", "examples"], "exit", None),
            ("G5", "Release consistency", ["python3", "scripts/release.py", "check"], "exit", None),
            ("G6", "Diff check", ["git", "diff", "--check"], "exit", None),
        ]
        return {
            "schema_version": 1,
            "project_id": "gpt-review-planner",
            "task_id": "a5cc93aa-ed68-403b-a6ce-717410719909",
            "task_sha256": "c9fb90624529092bb78663764694a5255072686a40ee17448c61102c75e4704e",
            "task_required_gates": [shlex.join(argv) for _, _, argv, _, _ in commands],
            "required_gates": [
                {
                    "id": gate_id,
                    "name": name,
                    "command": __import__("shlex").join(argv),
                    "argv": argv,
                    "env": {},
                    "cwd": "",
                    "parser": parser,
                    "metric": metric,
                    "timeout_seconds": 7200,
                    "max_output_bytes": 16777216,
                }
                for gate_id, name, argv, parser, metric in commands
            ],
        }

    def test_valid_contract_has_exact_order_and_task_gate(self):
        contract = self.contract()
        validate_contract(contract)
        self.assertEqual(contract["required_gates"][0]["command"], "python3 -m unittest tests.test_task_gate_contract -v")
        self.assertEqual([gate["id"] for gate in contract["required_gates"]], ["G1", "G2", "G3", "G4", "G5", "G6"])

    def assert_plan_mismatch(self, mutate):
        contract = self.contract()
        manifest = {"gates": manifest_gates(contract)}
        plan = gate_plan(contract)
        mutate(contract, manifest, plan)
        with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
            validate_generated_outputs(contract, manifest, plan)

    def test_rejects_stale_focused_gate(self):
        contract = self.contract()
        stale = ["python3 -m unittest tests.test_workflow_performance_budget -v"] + contract["task_required_gates"][1:]
        contract["task_required_gates"] = stale
        contract["required_gates"][0]["argv"] = shlex.split(stale[0])
        contract["required_gates"][0]["command"] = stale[0]
        with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
            validate_contract(contract, self.contract()["task_required_gates"])

    def test_rejects_sixth_gate_range_substitution(self):
        contract = self.contract()
        contract["required_gates"][5]["argv"] = ["git", "diff", "--check", "base..head", "--"]
        contract["required_gates"][5]["command"] = shlex.join(contract["required_gates"][5]["argv"])
        with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
            validate_contract(contract)

    def test_rejects_task_gate_count_and_order_mismatch(self):
        contract = self.contract()
        contract["task_required_gates"] = contract["task_required_gates"][:-1]
        with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
            validate_contract(contract)
        contract = self.contract()
        contract["required_gates"] = list(reversed(contract["required_gates"]))
        with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
            validate_contract(contract)

    def test_rejects_missing_extra_and_reordered_gates(self):
        for mutation in (
            lambda plan: plan["gates"].pop(),
            lambda plan: plan["gates"].append(copy.deepcopy(plan["gates"][0])),
            lambda plan: plan["gates"].reverse(),
        ):
            contract = self.contract(); manifest = {"gates": manifest_gates(contract)}; plan = gate_plan(contract); mutation(plan)
            with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
                validate_generated_outputs(contract, manifest, plan)

    def test_rejects_substituted_command_and_render_mismatch(self):
        contract = self.contract()
        contract["required_gates"][0]["argv"] = ["true"]
        with self.assertRaisesRegex(TaskGateContractError, r"placeholder command"):
            validate_contract(contract)
        contract = self.contract(); contract["required_gates"][0]["command"] = "python3 -m unittest"
        with self.assertRaisesRegex(TaskGateContractError, r"does not match argv"):
            validate_contract(contract)

    def test_rejects_contract_identity_mismatch_in_gate_run(self):
        contract = self.contract(); identity = contract_identity(contract)
        validate_gate_run_identity({"task_gate_contract": identity}, contract)
        for key in identity:
            bad = dict(identity); bad[key] = "wrong"
            with self.assertRaisesRegex(TaskGateContractError, r"TASK_GATE_CONTRACT_MISMATCH"):
                validate_gate_run_identity({"task_gate_contract": bad}, contract)

    def test_runner_requires_task_gate_contract(self):
        with tempfile.TemporaryDirectory() as raw:
            result = subprocess.run(
                ["python3", str(ROOT / "scripts/run-agent-gates.py"), "--repo", raw,
                 "--plan", str(Path(raw) / "plan.json"), "--implementation-commit", "0" * 40,
                 "--output-dir", str(Path(raw) / "out")],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("--task-gate-contract", result.stderr)

    def test_workflow_rejects_legacy_gate_plan_input(self):
        with tempfile.TemporaryDirectory() as raw:
            task = {
                "workflow": {},
                "manifest_seed": {},
                "evidence_plan": {},
                "task_gate_contract": self.contract(),
                "gate_plan": {"schema_version": 1, "gates": []},
            }
            task_path = Path(raw) / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            result = subprocess.run(
                ["python3", str(ROOT / "scripts/run-agent-evidence-workflow.py"), "run",
                 "--repo", str(ROOT), "--task", str(task_path)],
                text=True, capture_output=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("invalid task file", result.stderr + result.stdout)

    def test_generation_is_byte_stable_and_rejects_independent_manifest_gates(self):
        contract = self.contract()
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); contract_path = root / "task-gate-contract.json"; seed_path = root / "seed.json"
            out_manifest = root / "manifest.json"; out_plan = root / "gate-plan.json"
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            seed_path.write_text(json.dumps({"schema_version": 2, "title": "seed"}), encoding="utf-8")
            command = ["python3", str(ROOT / "scripts/generate-task-gate-contract.py"), "generate", "--contract", str(contract_path), "--manifest-seed", str(seed_path), "--manifest-output", str(out_manifest), "--gate-plan-output", str(out_plan)]
            first = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            first_manifest, first_plan = out_manifest.read_bytes(), out_plan.read_bytes()
            out_manifest.unlink(); out_plan.unlink()
            second = subprocess.run(command, text=True, capture_output=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(first_manifest, out_manifest.read_bytes())
            self.assertEqual(first_plan, out_plan.read_bytes())
            seed_path.write_text(json.dumps({"schema_version": 2, "gates": []}), encoding="utf-8")
            rejected = subprocess.run(command, text=True, capture_output=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("TASK_GATE_CONTRACT_MISMATCH", rejected.stderr)


if __name__ == "__main__":
    unittest.main()
