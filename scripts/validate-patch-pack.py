#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

SCHEMA_VERSION = 1
VALIDATOR_NAME = "gpt-review-planner"
MAX_HANDOFF_BYTES = 128 * 1024
REQUIRED_FILES = (
    "README_FIRST.md",
    "AGENT_HANDOFF.md",
    "PATCH_SPEC.md",
    "BEHAVIOR_CONTRACT.md",
    "VALIDATION_REPORT.md",
    "manifest.json",
    "evidence.json",
    "scripts/patch_pack_scope.py",
    "scripts/verify-agent-evidence.py",
    "scripts/verify-agent-result.sh",
    "expected/acceptance-gates.md",
    "expected/allowed-deviations.md",
)
REQUIRED_HANDOFF_HEADINGS = (
    "TASK_IDENTITY",
    "AUTHORITY",
    "AGENT_ROLE",
    "PROHIBITED_ACTIONS",
    "PATCH_APPLICATION",
    "REQUIRED_RUNTIME_GATES",
    "REPAIR_POLICY",
    "EVIDENCE_AND_COMMITS",
    "RESPONSE_CONTRACT",
)
MANIFEST_KEYS = {
    "schema_version", "patch_id", "title", "description", "created_at",
    "patch_timestamp", "patch_slug", "baseline_release", "evidence_directory",
    "workflow", "target", "files_created", "files_modified", "files_deleted",
    "requirements", "gates", "gpt_static_checks_performed",
    "gpt_runtime_checks_not_performed", "known_integration_risks",
    "forbidden_deviations",
}
EVIDENCE_KEYS = {"schema_version", "implementation_commit", "requirements", "gates", "deviations"}
TRANSPORT_ONLY_KEYS = {
    "gateway_id", "project_id", "task_id", "task_execution_mode", "bundle_sha256",
    "base64", "content_base64", "result_path", "airelay_session", "session_key",
}
COMPETING_INSTRUCTION_FILES = ("AGENT_TASK.md", "AGENT_REQUEST.md", "agent-request.md")
PATCH_ID_RE = re.compile(r"^patch-(\d{8}-\d{6})-([a-z0-9]+(?:-[a-z0-9]+){0,2})$")
BASELINE_RE = re.compile(r"^v\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
PLACEHOLDER_PATTERNS = (
    re.compile(r"(?<![A-Za-z0-9])REPLACE_WITH_[A-Z0-9_]+"),
    re.compile(r"(?<![A-Za-z0-9])REPLACE_[A-Z0-9_]+"),
    re.compile(r"TODO:\s*fill\b", re.IGNORECASE),
    re.compile(r"TBD:\s*fill\b", re.IGNORECASE),
    re.compile(r"\{\{PLACEHOLDER\}\}"),
    re.compile(r"\$\{REPLACE_VALUE\}"),
)


@dataclass(frozen=True)
class Finding:
    code: str
    path: str | None
    message: str

    def as_json(self) -> dict[str, object]:
        return {"code": self.code, "path": self.path, "message": self.message}


class DuplicateKeyError(ValueError):
    pass


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, label: str, findings: list[Finding]) -> dict[str, Any] | None:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        findings.append(Finding("missing_json", path.name, f"Missing {label}: {exc}"))
        return None
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=strict_object)
    except UnicodeDecodeError as exc:
        findings.append(Finding("invalid_json_encoding", path.name, f"{label} is not UTF-8: {exc}"))
        return None
    except (json.JSONDecodeError, DuplicateKeyError) as exc:
        findings.append(Finding("invalid_json", path.name, f"Invalid {label}: {exc}"))
        return None
    if not isinstance(value, dict):
        findings.append(Finding("invalid_json_root", path.name, f"{label} root must be an object."))
        return None
    return value


def repository_version() -> str:
    try:
        value = (Path(__file__).resolve().parents[1] / "VERSION").read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"
    return value or "unknown"


def workflow_commit() -> str | None:
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD^{commit}"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    value = result.stdout.strip()
    return value if result.returncode == 0 and SHA_RE.fullmatch(value) else None


def require_regular_file(root: Path, relative: str, findings: list[Finding]) -> Path | None:
    path = root / relative
    if path.is_symlink():
        findings.append(Finding("symlink_required_file", relative, f"Required file must not be a symlink: {relative}"))
        return None
    if not path.is_file():
        code = "missing_agent_handoff" if relative == "AGENT_HANDOFF.md" else "missing_required_file"
        message = "Missing required AGENT_HANDOFF.md." if relative == "AGENT_HANDOFF.md" else f"Missing required file: {relative}."
        findings.append(Finding(code, relative, message))
        return None
    return path


def validate_manifest(manifest: dict[str, Any], findings: list[Finding]) -> tuple[list[str], list[str]]:
    unknown = set(manifest) - MANIFEST_KEYS
    for key in sorted(unknown):
        code = "transport_field_in_manifest" if key in TRANSPORT_ONLY_KEYS else "unknown_manifest_field"
        findings.append(Finding(code, "manifest.json", f"Unknown manifest field: {key}."))
    missing = MANIFEST_KEYS - set(manifest)
    for key in sorted(missing):
        findings.append(Finding("missing_manifest_field", "manifest.json", f"Missing manifest field: {key}."))

    if manifest.get("schema_version") != 2:
        findings.append(Finding("invalid_manifest_schema", "manifest.json", "manifest.schema_version must be 2."))
    patch_id = manifest.get("patch_id")
    match = PATCH_ID_RE.fullmatch(patch_id) if isinstance(patch_id, str) else None
    if not match:
        findings.append(Finding("invalid_patch_id", "manifest.json", "manifest.patch_id must be patch-YYYYMMDD-HHMMSS-<one-to-three-word-slug>."))
    else:
        if manifest.get("patch_timestamp") != match.group(1) or manifest.get("patch_slug") != match.group(2):
            findings.append(Finding("patch_identity_mismatch", "manifest.json", "manifest timestamp and slug must match patch_id."))
    baseline = manifest.get("baseline_release")
    if not isinstance(baseline, str) or not BASELINE_RE.fullmatch(baseline):
        findings.append(Finding("invalid_baseline_release", "manifest.json", "manifest.baseline_release must be a v-prefixed semantic version."))
    if isinstance(patch_id, str) and isinstance(baseline, str):
        expected = f".gpt-review/evidence/{baseline}/{patch_id}"
        if manifest.get("evidence_directory") != expected:
            findings.append(Finding("invalid_evidence_directory", "manifest.json", f"manifest.evidence_directory must equal {expected}."))
    created_at = manifest.get("created_at")
    if isinstance(created_at, str):
        try:
            parsed = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            findings.append(Finding("invalid_created_at", "manifest.json", "manifest.created_at must use YYYY-MM-DDTHH:MM:SSZ."))
        else:
            if parsed.strftime("%Y%m%d-%H%M%S") != manifest.get("patch_timestamp"):
                findings.append(Finding("created_at_mismatch", "manifest.json", "manifest.created_at and patch_timestamp disagree."))
    else:
        findings.append(Finding("invalid_created_at", "manifest.json", "manifest.created_at must be a string."))

    workflow = manifest.get("workflow")
    if not isinstance(workflow, dict):
        findings.append(Finding("invalid_workflow_identity", "manifest.json", "manifest.workflow must be an object."))
    else:
        expected = {"repository", "version", "commit", "document"}
        if set(workflow) != expected:
            findings.append(Finding("invalid_workflow_identity", "manifest.json", "manifest.workflow must contain exactly repository, version, commit, and document."))
        if not isinstance(workflow.get("repository"), str) or not workflow.get("repository"):
            findings.append(Finding("invalid_workflow_repository", "manifest.json", "workflow.repository must be non-empty."))
        if not isinstance(workflow.get("version"), str) or not workflow.get("version"):
            findings.append(Finding("invalid_workflow_version", "manifest.json", "workflow.version must be non-empty."))
        if not isinstance(workflow.get("commit"), str) or not SHA_RE.fullmatch(workflow.get("commit", "")):
            findings.append(Finding("invalid_workflow_commit", "manifest.json", "workflow.commit must be a lowercase 40-character Git SHA."))
        if workflow.get("document") != "GPT_REVIEW_PLANNER.md":
            findings.append(Finding("invalid_workflow_document", "manifest.json", "workflow.document must be GPT_REVIEW_PLANNER.md."))

    target = manifest.get("target")
    if not isinstance(target, dict):
        findings.append(Finding("invalid_target_identity", "manifest.json", "manifest.target must be an object."))
    else:
        expected = {"repository", "branch", "base_revision"}
        if set(target) != expected:
            findings.append(Finding("invalid_target_identity", "manifest.json", "manifest.target must contain exactly repository, branch, and base_revision."))
        for key in ("repository", "branch"):
            if not isinstance(target.get(key), str) or not target.get(key):
                findings.append(Finding(f"invalid_target_{key}", "manifest.json", f"target.{key} must be non-empty."))
        if not isinstance(target.get("base_revision"), str) or not SHA_RE.fullmatch(target.get("base_revision", "")):
            findings.append(Finding("invalid_target_base", "manifest.json", "target.base_revision must be a lowercase 40-character Git SHA."))

    def ids(label: str) -> list[str]:
        raw = manifest.get(label)
        if not isinstance(raw, list) or not raw:
            findings.append(Finding(f"invalid_{label}", "manifest.json", f"manifest.{label} must be a non-empty array."))
            return []
        result: list[str] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"]:
                findings.append(Finding(f"invalid_{label}_item", "manifest.json", f"manifest.{label}[{index}] must contain a non-empty id."))
                continue
            result.append(item["id"])
            if label == "gates" and item.get("kind") == "github-actions" and item.get("head") != "implementation":
                findings.append(Finding("invalid_github_actions_head", "manifest.json", "GitHub Actions gates must target head=implementation."))
        if len(result) != len(set(result)):
            findings.append(Finding(f"duplicate_{label}_id", "manifest.json", f"manifest.{label} contains duplicate IDs."))
        return result

    return ids("requirements"), ids("gates")


def section_map(text: str) -> dict[str, str]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    positions: list[tuple[int, str]] = []
    for index, line in enumerate(lines):
        match = re.fullmatch(r"## ([A-Z][A-Z0-9_]*)", line)
        if match:
            positions.append((index, match.group(1)))
    result: dict[str, str] = {}
    for pos_index, (start, name) in enumerate(positions):
        end = positions[pos_index + 1][0] if pos_index + 1 < len(positions) else len(lines)
        result[name] = "\n".join(lines[start + 1:end]).strip()
    return result


def validate_handoff(path: Path, manifest: dict[str, Any] | None, findings: list[Finding], warnings: list[Finding]) -> bytes | None:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        findings.append(Finding("unreadable_agent_handoff", "AGENT_HANDOFF.md", f"Could not read AGENT_HANDOFF.md: {exc}"))
        return None
    if len(raw) > MAX_HANDOFF_BYTES:
        findings.append(Finding("oversized_agent_handoff", "AGENT_HANDOFF.md", f"AGENT_HANDOFF.md exceeds {MAX_HANDOFF_BYTES} bytes."))
    if b"\0" in raw:
        findings.append(Finding("nul_agent_handoff", "AGENT_HANDOFF.md", "AGENT_HANDOFF.md contains a NUL byte."))
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        findings.append(Finding("invalid_agent_handoff_utf8", "AGENT_HANDOFF.md", f"AGENT_HANDOFF.md is not UTF-8: {exc}"))
        return raw
    if not text.strip():
        findings.append(Finding("empty_agent_handoff", "AGENT_HANDOFF.md", "AGENT_HANDOFF.md must not be empty."))
        return raw
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    if not lines or lines[0] != "# AGENT_HANDOFF":
        findings.append(Finding("invalid_agent_handoff_title", "AGENT_HANDOFF.md", "The first heading must be exactly # AGENT_HANDOFF."))
    sections = section_map(text)
    for heading in REQUIRED_HANDOFF_HEADINGS:
        if heading not in sections:
            findings.append(Finding("missing_agent_handoff_heading", "AGENT_HANDOFF.md", f"Missing required Markdown heading: ## {heading}."))
    if manifest:
        workflow = manifest.get("workflow") if isinstance(manifest.get("workflow"), dict) else {}
        target = manifest.get("target") if isinstance(manifest.get("target"), dict) else {}
        expected = {
            "Patch ID": manifest.get("patch_id"),
            "Workflow repository": workflow.get("repository"),
            "Workflow version": workflow.get("version"),
            "Workflow commit": workflow.get("commit"),
            "Workflow document": workflow.get("document"),
            "Target repository": target.get("repository"),
            "Target branch": target.get("branch"),
            "Base revision": target.get("base_revision"),
            "Evidence directory": manifest.get("evidence_directory"),
        }
        identity = sections.get("TASK_IDENTITY", "")
        for label, value in expected.items():
            line = f"- {label}: `{value}`"
            if identity.count(line) != 1:
                findings.append(Finding("handoff_identity_mismatch", "AGENT_HANDOFF.md", f"TASK_IDENTITY must contain exactly: {line}"))
    alias = path.with_name("AGENT_PROMPT.md")
    if alias.exists():
        if alias.is_symlink() or not alias.is_file():
            findings.append(Finding("invalid_agent_prompt_alias", "AGENT_PROMPT.md", "AGENT_PROMPT.md compatibility alias must be a regular file."))
        elif alias.read_bytes() != raw:
            findings.append(Finding("divergent_agent_prompt", "AGENT_PROMPT.md", "AGENT_PROMPT.md must be byte-identical to AGENT_HANDOFF.md when present."))
        else:
            warnings.append(Finding("deprecated_agent_prompt_alias", "AGENT_PROMPT.md", "AGENT_PROMPT.md is a deprecated one-release compatibility alias."))
    return raw


def validate_evidence(evidence: dict[str, Any], requirement_ids: list[str], gate_ids: list[str], findings: list[Finding]) -> None:
    unknown = set(evidence) - EVIDENCE_KEYS
    for key in sorted(unknown):
        findings.append(Finding("unknown_evidence_field", "evidence.json", f"Unknown evidence field: {key}."))
    for key in sorted(EVIDENCE_KEYS - set(evidence)):
        findings.append(Finding("missing_evidence_field", "evidence.json", f"Missing evidence field: {key}."))
    if evidence.get("schema_version") != 1:
        findings.append(Finding("invalid_evidence_schema", "evidence.json", "evidence.schema_version must be 1."))
    implementation = evidence.get("implementation_commit")
    if implementation != "REPLACE_IMPLEMENTATION_COMMIT" and not (isinstance(implementation, str) and SHA_RE.fullmatch(implementation)):
        findings.append(Finding("invalid_implementation_commit", "evidence.json", "Pre-execution implementation_commit must be the canonical placeholder or a Git SHA."))

    def collect(label: str, expected: list[str]) -> None:
        raw = evidence.get(label)
        if not isinstance(raw, list):
            findings.append(Finding(f"invalid_evidence_{label}", "evidence.json", f"evidence.{label} must be an array."))
            return
        ids: list[str] = []
        for index, item in enumerate(raw):
            if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                findings.append(Finding(f"invalid_evidence_{label}_item", "evidence.json", f"evidence.{label}[{index}] must contain an id."))
                continue
            ids.append(item["id"])
            if item.get("status") != "pending":
                findings.append(Finding("non_pending_evidence", "evidence.json", f"Pre-execution evidence.{label}[{index}] must be pending."))
        if ids != expected:
            findings.append(Finding(f"evidence_{label}_id_mismatch", "evidence.json", f"evidence.{label} IDs and order must exactly match manifest.{label}."))
    collect("requirements", requirement_ids)
    collect("gates", gate_ids)
    if evidence.get("deviations") != []:
        findings.append(Finding("initial_deviations_not_empty", "evidence.json", "Pre-execution deviations must be empty."))


def scan_placeholders(root: Path, findings: list[Finding]) -> None:
    for path in sorted(root.rglob("*")):
        if path.is_symlink() or not path.is_file() or path.name == ".gitkeep":
            continue
        relative = path.relative_to(root).as_posix()
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern in PLACEHOLDER_PATTERNS:
            for match in pattern.finditer(text):
                value = match.group(0)
                if relative == "evidence.json" and value == "REPLACE_IMPLEMENTATION_COMMIT":
                    continue
                findings.append(Finding("unresolved_placeholder", relative, f"Unresolved placeholder: {value}"))
                break


def invoke_scope_validator(root: Path, findings: list[Finding]) -> None:
    path = Path(__file__).with_name("patch_pack_scope.py")
    if not path.is_file():
        findings.append(Finding("missing_scope_validator", "scripts/patch_pack_scope.py", "Planner scope validator is missing."))
        return
    try:
        spec = importlib.util.spec_from_file_location("planner_patch_pack_scope", path)
        if spec is None or spec.loader is None:
            raise RuntimeError("module spec is unavailable")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        errors = module.validate_pack(root)
    except Exception as exc:  # dependency-free validator must fail closed
        findings.append(Finding("scope_validator_failure", "scripts/patch_pack_scope.py", f"Scope validator failed: {exc}"))
        return
    for message in errors:
        findings.append(Finding("scope_mismatch", None, message))


def validate(root: Path) -> tuple[dict[str, Any] | None, list[Finding], list[Finding]]:
    findings: list[Finding] = []
    warnings: list[Finding] = []
    required: dict[str, Path] = {}
    for relative in REQUIRED_FILES:
        path = require_regular_file(root, relative, findings)
        if path:
            required[relative] = path
    for relative in COMPETING_INSTRUCTION_FILES:
        if (root / relative).exists():
            findings.append(Finding("competing_instruction_source", relative, f"Competing normative instruction file is forbidden: {relative}."))

    manifest = load_json(root / "manifest.json", "manifest.json", findings) if (root / "manifest.json").is_file() else None
    requirement_ids: list[str] = []
    gate_ids: list[str] = []
    if manifest is not None:
        requirement_ids, gate_ids = validate_manifest(manifest, findings)
    handoff = required.get("AGENT_HANDOFF.md")
    if handoff:
        validate_handoff(handoff, manifest, findings, warnings)
    evidence = load_json(root / "evidence.json", "evidence.json", findings) if (root / "evidence.json").is_file() else None
    if evidence is not None:
        validate_evidence(evidence, requirement_ids, gate_ids, findings)
    scan_placeholders(root, findings)
    invoke_scope_validator(root, findings)
    return manifest, findings, warnings


def result_document(manifest: dict[str, Any] | None, findings: Iterable[Finding], warnings: Iterable[Finding]) -> dict[str, object]:
    errors = [item.as_json() for item in findings]
    warning_items = [item.as_json() for item in warnings]
    return {
        "schema_version": SCHEMA_VERSION,
        "valid": not errors,
        "validator": VALIDATOR_NAME,
        "validator_version": repository_version(),
        "workflow_commit": workflow_commit(),
        "patch_id": manifest.get("patch_id") if manifest else None,
        "errors": errors,
        "warnings": warning_items,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate a GPT Review Planner Executable Patch Pack.")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    parser.add_argument("patch_pack", type=Path)
    args = parser.parse_args(argv)
    root = args.patch_pack.resolve()
    manifest, findings, warnings = validate(root)
    document = result_document(manifest, findings, warnings)
    if args.format == "json":
        print(json.dumps(document, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    else:
        for warning in warnings:
            print(f"WARNING [{warning.code}]: {warning.message}", file=sys.stderr)
        if findings:
            for finding in findings:
                location = f" ({finding.path})" if finding.path else ""
                print(f"ERROR [{finding.code}]{location}: {finding.message}", file=sys.stderr)
        else:
            print(f"PASS: {root}")
    return 0 if document["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
