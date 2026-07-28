#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
MODES = ("manual-download", "gateway-task-bundle", "prompt-only", "no-action")
PACK_MODES = {"manual-download", "gateway-task-bundle"}
NO_ACTION_SENTENCE = "No agent action is required. Preserve the reported state and wait for the next owner instruction."
GATEWAY_SENTENCE = "Execute the materialized patch pack using AGENT_HANDOFF.md."


@dataclass(frozen=True)
class Finding:
    code: str
    path: str | None
    message: str

    def as_json(self) -> dict[str, object]:
        return {"code": self.code, "path": self.path, "message": self.message}


def require_file(path: Path, code: str, label: str, findings: list[Finding]) -> Path | None:
    if path.is_symlink() or not path.is_file():
        findings.append(Finding(code, path.name, f"Missing regular {label}: {path}"))
        return None
    return path


def run_semantic(planner: Path, pack: Path, findings: list[Finding]) -> dict[str, Any] | None:
    script = planner / "scripts/validate-patch-pack.py"
    if not script.is_file():
        findings.append(Finding("missing_semantic_validator", str(script), "Pinned semantic validator is missing."))
        return None
    result = subprocess.run(
        [sys.executable, str(script), "--format", "json", str(pack)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        findings.append(Finding("semantic_validator_protocol_error", str(script), f"Semantic validator did not return JSON: {exc}"))
        return None
    if result.returncode != 0 or payload.get("valid") is not True:
        findings.append(Finding("semantic_validation_failed", str(pack), "Canonical semantic validation failed."))
    return payload


def exact_final_block(text: str, sentence: str) -> bool:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
    expected = f"## AGENT_HANDOFF\n\n{sentence}"
    marker = normalized.rfind("\n## AGENT_HANDOFF\n")
    if normalized.startswith("## AGENT_HANDOFF\n"):
        marker = 0
    if marker < 0:
        return False
    block = normalized[marker + (1 if marker else 0):]
    return block == expected


def validate_response(path: Path, mode: str, archive: str | None, sidecar: str | None, findings: list[Finding]) -> None:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        findings.append(Finding("invalid_response_file", str(path), f"Could not read response file: {exc}"))
        return
    if mode == "manual-download":
        assert archive and sidecar
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        for marker, expected in (("PATCH_PACK_NAME", archive), ("SHA256_FILE_NAME", sidecar)):
            positions = [index for index, line in enumerate(lines) if line == marker]
            if len(positions) != 1 or positions[0] + 1 >= len(lines) or lines[positions[0] + 1] != expected:
                findings.append(Finding("invalid_manual_filename_field", str(path), f"{marker} must occur once and be followed by {expected}."))
        sentence = f"Apply patch pack `{archive}` from the Downloads folder."
        if not exact_final_block(text, sentence):
            findings.append(Finding("invalid_manual_handoff", str(path), "Manual response must end with the canonical Downloads handoff."))
    elif mode == "gateway-task-bundle":
        if not exact_final_block(text, GATEWAY_SENTENCE):
            findings.append(Finding("invalid_gateway_handoff", str(path), "Gateway response must end with the transport-neutral materialized-pack handoff."))
    elif mode == "no-action":
        if not exact_final_block(text, NO_ACTION_SENTENCE):
            findings.append(Finding("invalid_no_action_handoff", str(path), "No-action response must end with the canonical no-action sentence."))
    else:
        normalized = text.replace("\r\n", "\n").replace("\r", "\n").rstrip()
        marker = normalized.rfind("\n## AGENT_HANDOFF\n")
        if normalized.startswith("## AGENT_HANDOFF\n"):
            marker = 0
        if marker < 0 or not normalized[marker + (1 if marker else 0):].startswith("## AGENT_HANDOFF\n\n"):
            findings.append(Finding("invalid_prompt_only_handoff", str(path), "Prompt-only response must end with a non-empty AGENT_HANDOFF section."))


def validate_tools(pack: Path, planner: Path, findings: list[Finding]) -> None:
    tools = (
        ("patch_pack_scope.py", "python"),
        ("verify-agent-evidence.py", "python"),
        ("verify-agent-result.sh", "shell"),
    )
    for name, kind in tools:
        bundled = require_file(pack / "scripts" / name, "missing_bundled_tool", f"bundled {name}", findings)
        canonical = require_file(planner / "scripts" / name, "missing_planner_tool", f"planner {name}", findings)
        if not bundled or not canonical:
            continue
        if bundled.read_bytes() != canonical.read_bytes():
            findings.append(Finding("bundled_tool_mismatch", f"scripts/{name}", f"Bundled {name} is not byte-identical to the pinned planner tool."))
            continue
        command = [sys.executable, str(bundled), "--help"] if kind == "python" else ["bash", str(bundled), "--help"]
        result = subprocess.run(command, check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            findings.append(Finding("bundled_tool_startup_failed", f"scripts/{name}", f"Bundled {name} failed --help with exit {result.returncode}."))


def validate(args: argparse.Namespace) -> tuple[str | None, list[Finding], dict[str, Any] | None]:
    findings: list[Finding] = []
    semantic: dict[str, Any] | None = None
    patch_id: str | None = None
    archive: str | None = None
    sidecar: str | None = None
    if args.archive_name:
        archive = args.archive_name
    if args.sidecar_name:
        sidecar = args.sidecar_name
    if args.mode in PACK_MODES:
        if args.pack_root is None or args.planner_root is None:
            findings.append(Finding("missing_pack_arguments", None, "Pack delivery modes require --pack-root and --planner-root."))
        else:
            pack = args.pack_root.resolve()
            planner = args.planner_root.resolve()
            semantic = run_semantic(planner, pack, findings)
            if semantic and isinstance(semantic.get("patch_id"), str):
                patch_id = semantic["patch_id"]
                expected_archive = f"{patch_id}.tar.gz"
                expected_sidecar = f"{expected_archive}.sha256"
                if archive != expected_archive:
                    findings.append(Finding("wrong_archive_basename", None, f"Archive basename must be {expected_archive}."))
                if sidecar != expected_sidecar:
                    findings.append(Finding("wrong_sidecar_basename", None, f"Sidecar basename must be {expected_sidecar}."))
            validate_tools(pack, planner, findings)
    if args.response_file is None:
        findings.append(Finding("missing_response_file", None, "Every delivery mode requires --response-file."))
    else:
        validate_response(args.response_file, args.mode, archive, sidecar, findings)
    return patch_id, findings, semantic


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate patch-pack delivery without implementing gateway transport.")
    parser.add_argument("--mode", choices=MODES, default="manual-download")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("--pack-root", type=Path)
    parser.add_argument("--planner-root", type=Path)
    parser.add_argument("--archive-name")
    parser.add_argument("--sidecar-name")
    parser.add_argument("--response-file", type=Path)
    args = parser.parse_args(argv)
    patch_id, findings, semantic = validate(args)
    document = {
        "schema_version": SCHEMA_VERSION,
        "valid": not findings,
        "validator": "gpt-review-planner-delivery",
        "mode": args.mode,
        "patch_id": patch_id,
        "errors": [item.as_json() for item in findings],
        "warnings": [] if semantic is None else semantic.get("warnings", []),
    }
    if args.format == "json":
        print(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    elif findings:
        for finding in findings:
            location = f" ({finding.path})" if finding.path else ""
            print(f"ERROR [{finding.code}]{location}: {finding.message}", file=sys.stderr)
    else:
        print(f"Patch-pack delivery validation ({args.mode}): PASS")
    return 0 if document["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
