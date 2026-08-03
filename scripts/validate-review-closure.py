#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

EXPECTED_KEYS = {
    "schema_version",
    "protocol_id",
    "initial_review_mode",
    "post_implementation_review_mode",
    "max_normal_correction_rounds",
    "blocker_bases",
    "non_blocking_classes",
    "reopen_bases",
    "finding_states",
    "required_output_queues",
    "closure_verdicts",
    "stop_rule",
}
REQUIRED_BLOCKERS = {
    "acceptance_criterion_failure",
    "demonstrable_regression",
    "critical_or_high_preexisting_defect",
    "security_vulnerability",
    "data_loss_or_corruption",
    "broken_public_contract",
    "required_gate_failure",
    "materially_unusable_feature",
}
REQUIRED_NON_BLOCKING = {
    "hardening",
    "documentation_completeness",
    "maintainability",
    "optional_test_expansion",
    "future_architecture",
    "style_preference",
    "stronger_unapproved_contract",
}
REQUIRED_REOPEN = {
    "owner_request",
    "material_architecture_change",
    "new_critical_or_high_evidence",
}
REQUIRED_STATES = {
    "open", "in_progress", "verified_closed", "deferred", "superseded"
}
REQUIRED_QUEUES = {"MERGE_BLOCKERS", "FOLLOW_UP_BACKLOG", "OBSERVATIONS"}
REQUIRED_VERDICTS = {"CORRECTION_REQUIRED", "OWNER_DECISION_REQUIRED", "MERGE_READY"}
STOP_KEYS = {
    "all_acceptance_criteria_pass", "required_gates_pass",
    "open_merge_blockers", "verdict", "stop_after_verdict"
}


class ContractError(ValueError):
    pass


def validate_release_task(task_path: Path, repo: Path | None = None) -> dict[str, str]:
    validator_path = Path(__file__).with_name("validate-release-lifecycle-task.py")
    spec = importlib.util.spec_from_file_location("release_lifecycle_task", validator_path)
    if spec is None or spec.loader is None:
        raise ContractError("release lifecycle validator is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        data = json.loads(task_path.read_text(encoding="utf-8"), object_pairs_hook=module.unique_pairs)
        result = module.validate_task(data)
    except (OSError, UnicodeError, json.JSONDecodeError, module.LifecycleError) as exc:
        raise ContractError(f"release lifecycle task is invalid: {exc}") from exc
    if repo is not None:
        release_script = repo / "scripts" / "release.py"
        ci_script = repo / "scripts" / "check-github-ci.py"
        if release_script.is_symlink() or not release_script.is_file():
            raise ContractError("attached project release script is missing or not regular")
        if ci_script.is_symlink() or not ci_script.is_file():
            raise ContractError("attached project CI script is missing or not regular")
        command = [sys.executable, str(release_script), "--repo", str(repo)]
        command.append("check-source" if result.get("lifecycle_mode") == "implementation_unreleased" else "check-release-ready")
        check = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
        if check.returncode != 0:
            raise ContractError("release lifecycle state gate failed: " + (check.stderr.strip() or "unknown error"))
        conformance = subprocess.run(
            [
                sys.executable,
                str(Path(__file__).with_name("validate-release-tool-conformance.py")),
                "--release-script",
                str(release_script),
                "--ci-script",
                str(ci_script),
                "--canonical-script",
                str(Path(__file__).with_name("release.py")),
            ],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if conformance.returncode != 0:
            raise ContractError("release tool conformance failed: " + (conformance.stderr.strip() or "unknown error"))
    return result


def strict_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractError(f"{label} must be a non-empty string")
    if value != value.strip():
        raise ContractError(f"{label} must not contain surrounding whitespace")
    if any(ord(character) < 0x20 or ord(character) == 0x7F for character in value):
        raise ContractError(f"{label} contains an ASCII control character")
    return value


def string_set(value: Any, label: str) -> set[str]:
    if not isinstance(value, list) or not value:
        raise ContractError(f"{label} must be a non-empty array")
    result: set[str] = set()
    for index, item in enumerate(value):
        text = strict_text(item, f"{label}[{index}]")
        if text in result:
            raise ContractError(f"{label} contains duplicate value: {text}")
        result.add(text)
    return result


def require_exact(actual: set[str], expected: set[str], label: str) -> None:
    missing = expected - actual
    extra = actual - expected
    if missing or extra:
        details = []
        if missing:
            details.append("missing=" + ",".join(sorted(missing)))
        if extra:
            details.append("extra=" + ",".join(sorted(extra)))
        raise ContractError(f"{label} contract mismatch: {'; '.join(details)}")


def validate_contract(data: Any) -> dict[str, int]:
    if not isinstance(data, dict):
        raise ContractError("contract root must be an object")
    unknown = set(data) - EXPECTED_KEYS
    missing = EXPECTED_KEYS - set(data)
    if unknown:
        raise ContractError("unknown top-level fields: " + ", ".join(sorted(unknown)))
    if missing:
        raise ContractError("missing top-level fields: " + ", ".join(sorted(missing)))
    if data["schema_version"] != 1:
        raise ContractError("schema_version must be 1")
    if data["protocol_id"] != "bounded-review-closure":
        raise ContractError("protocol_id must be bounded-review-closure")
    if data["initial_review_mode"] != "full":
        raise ContractError("initial_review_mode must be full")
    if data["post_implementation_review_mode"] != "delta":
        raise ContractError("post_implementation_review_mode must be delta")
    if data["max_normal_correction_rounds"] != 1 or isinstance(data["max_normal_correction_rounds"], bool):
        raise ContractError("max_normal_correction_rounds must be integer 1")

    blockers = string_set(data["blocker_bases"], "blocker_bases")
    non_blocking = string_set(data["non_blocking_classes"], "non_blocking_classes")
    reopen = string_set(data["reopen_bases"], "reopen_bases")
    states = string_set(data["finding_states"], "finding_states")
    queues = string_set(data["required_output_queues"], "required_output_queues")
    verdicts = string_set(data["closure_verdicts"], "closure_verdicts")

    require_exact(blockers, REQUIRED_BLOCKERS, "blocker_bases")
    require_exact(non_blocking, REQUIRED_NON_BLOCKING, "non_blocking_classes")
    require_exact(reopen, REQUIRED_REOPEN, "reopen_bases")
    require_exact(states, REQUIRED_STATES, "finding_states")
    require_exact(queues, REQUIRED_QUEUES, "required_output_queues")
    require_exact(verdicts, REQUIRED_VERDICTS, "closure_verdicts")
    if blockers & non_blocking:
        raise ContractError("blocker and non-blocking classes overlap")

    stop = data["stop_rule"]
    if not isinstance(stop, dict) or set(stop) != STOP_KEYS:
        raise ContractError("stop_rule fields are invalid")
    expected_stop = {
        "all_acceptance_criteria_pass": True,
        "required_gates_pass": True,
        "open_merge_blockers": 0,
        "verdict": "MERGE_READY",
        "stop_after_verdict": True,
    }
    if stop != expected_stop:
        raise ContractError("stop_rule does not encode the mandatory MERGE_READY stop condition")

    return {
        "blockers": len(blockers),
        "non_blocking": len(non_blocking),
        "reopen": len(reopen),
        "states": len(states),
        "queues": len(queues),
        "verdicts": len(verdicts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the bounded review closure contract.")
    parser.add_argument(
        "contract",
        nargs="?",
        type=Path,
        default=Path("profiles/review-closure.json"),
    )
    parser.add_argument("--release-task", type=Path)
    parser.add_argument("--repo", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.contract.read_text(encoding="utf-8"))
        counts = validate_contract(data)
        if args.release_task:
            validate_release_task(args.release_task, args.repo.resolve() if args.repo else None)
    except (OSError, json.JSONDecodeError, ContractError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(
        "PASS: bounded review closure contract "
        + " ".join(f"{key}={value}" for key, value in counts.items())
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
