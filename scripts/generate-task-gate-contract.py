#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_gate_contract import (  # noqa: E402
    TaskGateContractError,
    atomic_write,
    gate_plan,
    load_json,
    manifest_gates,
    validate_contract,
    validate_generated_outputs,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--contract", required=True, type=Path)
    validate.add_argument("--task-required-gates", type=Path)
    generate = sub.add_parser("generate")
    generate.add_argument("--contract", required=True, type=Path)
    generate.add_argument("--manifest-seed", required=True, type=Path)
    generate.add_argument("--manifest-output", required=True, type=Path)
    generate.add_argument("--gate-plan-output", required=True, type=Path)
    generate.add_argument("--task-required-gates", type=Path)
    args = parser.parse_args()
    try:
        authoritative = None
        if getattr(args, "task_required_gates", None) is not None:
            raw = json.loads(args.task_required_gates.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                raise TaskGateContractError("authoritative task gates must be an array")
            authoritative = raw
        contract = validate_contract(load_json(args.contract), authoritative)
        if args.command == "validate":
            print("PASS: task gate contract")
            return 0
        seed = load_json(args.manifest_seed)
        if "gates" in seed:
            raise TaskGateContractError(
                "TASK_GATE_CONTRACT_MISMATCH: manifest seed must not contain gates"
            )
        manifest = dict(seed)
        manifest["gates"] = manifest_gates(contract)
        plan = gate_plan(contract)
        atomic_write(args.manifest_output, manifest)
        atomic_write(args.gate_plan_output, plan)
        validate_generated_outputs(contract, load_json(args.manifest_output), load_json(args.gate_plan_output))
        print(f"Task gate contract generated: manifest={args.manifest_output} plan={args.gate_plan_output}")
        return 0
    except (TaskGateContractError, OSError, KeyError) as exc:
        print(f"TASK_GATE_CONTRACT_MISMATCH: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
