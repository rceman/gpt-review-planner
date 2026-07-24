#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
SEMVER_TAG_RE = re.compile(
    r"^v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
PATCH_ID_RE = re.compile(r"^patch-(\d{8}-\d{6})-([a-z0-9]+(?:-[a-z0-9]+){0,2})$")
PROOF_TEXT_KINDS = {"source", "test", "workflow", "documentation"}
REQUIREMENT_STATUSES = {"pass", "partial", "fail", "na"}
GATE_STATUSES = {"pass", "fail", "skip"}
EVIDENCE_FILES = ("manifest.json", "evidence.json")
MAX_PROOF_LINES = 160


class EvidenceError(RuntimeError):
    pass


def git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if check and result.returncode != 0:
        message = result.stderr.decode("utf-8", errors="replace").strip()
        if not message:
            message = result.stdout.decode("utf-8", errors="replace").strip()
        raise EvidenceError(message or "git command failed")
    return result


def normalize_repo_path(raw: str, source: str) -> str:
    if raw == "" or any(character in raw for character in ("\0", "\n", "\r")):
        raise EvidenceError(f"{source}: invalid repository path")
    if "\\" in raw:
        raise EvidenceError(f"{source}: repository paths must use '/' separators")
    path = PurePosixPath(raw)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise EvidenceError(f"{source}: path must be normalized and repository-relative: {raw!r}")
    return raw


def load_json_bytes(path: Path, label: str) -> tuple[dict[str, Any], bytes]:
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise EvidenceError(f"missing {label}: {path}") from exc
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise EvidenceError(f"{label} must contain a JSON object")
    return value, raw


def require_string(data: dict[str, Any], key: str, label: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise EvidenceError(f"{label}.{key} must be a non-empty string")
    return value


def require_sha(value: str, field: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise EvidenceError(f"{field} must be a lowercase 40-character Git SHA")
    return value


def validate_manifest_identity(manifest: dict[str, Any]) -> Path:
    if manifest.get("schema_version") != 2:
        raise EvidenceError("manifest.schema_version must be 2")
    patch_id = require_string(manifest, "patch_id", "manifest")
    timestamp = require_string(manifest, "patch_timestamp", "manifest")
    slug = require_string(manifest, "patch_slug", "manifest")
    baseline = require_string(manifest, "baseline_release", "manifest")
    created_at = require_string(manifest, "created_at", "manifest")
    title = require_string(manifest, "title", "manifest")
    description = require_string(manifest, "description", "manifest")
    evidence_directory = require_string(manifest, "evidence_directory", "manifest")

    match = PATCH_ID_RE.fullmatch(patch_id)
    if not match:
        raise EvidenceError("manifest.patch_id must be patch-YYYYMMDD-HHMMSS-<1-to-3-word-slug>")
    if match.group(1) != timestamp or match.group(2) != slug:
        raise EvidenceError("manifest timestamp/slug must match patch_id")
    if not SEMVER_TAG_RE.fullmatch(baseline):
        raise EvidenceError("manifest.baseline_release must be a v-prefixed semantic version")
    try:
        parsed = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise EvidenceError("manifest.created_at must use UTC format YYYY-MM-DDTHH:MM:SSZ") from exc
    if parsed.strftime("%Y%m%d-%H%M%S") != timestamp:
        raise EvidenceError("manifest.created_at and patch_timestamp disagree")
    if not 2 <= len(title.split()) <= 6 or len(title) > 80:
        raise EvidenceError("manifest.title must contain 2-6 words and at most 80 characters")
    if not description or len(description) > 240 or description[-1] not in ".!?":
        raise EvidenceError("manifest.description must be one short sentence ending in punctuation")

    expected = f".gpt-review/evidence/{baseline}/{patch_id}"
    if evidence_directory != expected:
        raise EvidenceError(f"manifest.evidence_directory must equal {expected}")
    normalized = normalize_repo_path(evidence_directory, "manifest.evidence_directory")
    return Path(*PurePosixPath(normalized).parts)


def manifest_scope(manifest: dict[str, Any]) -> tuple[set[str], set[str], set[str]]:
    output: list[set[str]] = []
    for key in ("files_created", "files_modified", "files_deleted"):
        value = manifest.get(key)
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise EvidenceError(f"manifest.{key} must be an array of strings")
        normalized = {normalize_repo_path(item, f"manifest.{key}") for item in value}
        if len(normalized) != len(value):
            raise EvidenceError(f"manifest.{key} contains duplicates")
        output.append(normalized)
    created, modified, deleted = output
    overlap = (created & modified) | (created & deleted) | (modified & deleted)
    if overlap:
        raise EvidenceError("manifest operation sets overlap: " + ", ".join(sorted(overlap)))
    return created, modified, deleted


def indexed_objects(manifest: dict[str, Any], key: str) -> dict[str, dict[str, Any]]:
    raw = manifest.get(key)
    if not isinstance(raw, list) or not raw:
        raise EvidenceError(f"manifest.{key} must be a non-empty array")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw, 1):
        if not isinstance(item, dict):
            raise EvidenceError(f"manifest.{key}[{index}] must be an object")
        item_id = require_string(item, "id", f"manifest.{key}[{index}]")
        if item_id in result:
            raise EvidenceError(f"manifest.{key} contains duplicate id: {item_id}")
        result[item_id] = item
    return result


def parse_name_status_z(data: bytes) -> tuple[set[str], set[str], set[str]]:
    fields = data.split(b"\0")
    created: set[str] = set()
    modified: set[str] = set()
    deleted: set[str] = set()
    index = 0
    while index < len(fields):
        raw_status = fields[index]
        index += 1
        if not raw_status:
            continue
        status = raw_status.decode("ascii", errors="strict")
        code = status[0]
        if index >= len(fields) or not fields[index]:
            raise EvidenceError(f"git diff status {status!r} is missing a path")
        old_or_path = fields[index].decode("utf-8", errors="strict")
        index += 1
        if code in {"R", "C"}:
            if index >= len(fields) or not fields[index]:
                raise EvidenceError(f"git diff status {status!r} is missing its destination")
            new_path = fields[index].decode("utf-8", errors="strict")
            index += 1
            old_or_path = normalize_repo_path(old_or_path, "git diff old path")
            new_path = normalize_repo_path(new_path, "git diff new path")
            if code == "R":
                deleted.add(old_or_path)
            created.add(new_path)
        else:
            path = normalize_repo_path(old_or_path, "git diff path")
            if code == "A":
                created.add(path)
            elif code == "D":
                deleted.add(path)
            elif code in {"M", "T"}:
                modified.add(path)
            else:
                raise EvidenceError(f"unsupported git diff status: {status}")
    return created, modified, deleted


def diff_scope(repo: Path, base: str, head: str, *, cached: bool = False) -> tuple[set[str], set[str], set[str]]:
    args = ["diff", "--name-status", "-z", "--find-renames", "--find-copies"]
    if cached:
        args.append("--cached")
    else:
        args.append(f"{base}..{head}")
    args.append("--")
    return parse_name_status_z(git(repo, *args).stdout)


def assert_scope(label: str, expected: tuple[set[str], set[str], set[str]], actual: tuple[set[str], set[str], set[str]]) -> None:
    names = ("created", "modified", "deleted")
    errors: list[str] = []
    for name, expected_set, actual_set in zip(names, expected, actual):
        if expected_set != actual_set:
            errors.append(f"{name}: expected={sorted(expected_set)!r}, actual={sorted(actual_set)!r}")
    if errors:
        raise EvidenceError(label + " scope mismatch: " + "; ".join(errors))


def git_file(repo: Path, commit: str, path: str, *, required: bool = True) -> bytes | None:
    result = git(repo, "show", f"{commit}:{path}", check=False)
    if result.returncode != 0:
        if required:
            raise EvidenceError(f"file not found at {commit}: {path}")
        return None
    return result.stdout


def json_pointer(data: Any, pointer: str, label: str) -> Any:
    if not pointer.startswith("/"):
        raise EvidenceError(f"{label}: JSON pointer must start with '/'")
    current = data
    for raw_part in pointer[1:].split("/"):
        part = raw_part.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict) and part in current:
            current = current[part]
        elif isinstance(current, list) and part.isdigit() and int(part) < len(current):
            current = current[int(part)]
        else:
            raise EvidenceError(f"{label}: JSON pointer not found: {pointer}")
    return current


def validate_proof(repo: Path, base: str, implementation: str, evidence_directory: Path, proof: Any, label: str) -> None:
    if not isinstance(proof, dict):
        raise EvidenceError(f"{label} must be an object")
    kind = require_string(proof, "kind", label)
    path = normalize_repo_path(require_string(proof, "path", label), f"{label}.path")
    evidence_prefix = evidence_directory.as_posix().rstrip("/") + "/"
    if path == evidence_directory.as_posix() or path.startswith(evidence_prefix):
        raise EvidenceError(f"{label} must not cite evidence files")

    if kind in PROOF_TEXT_KINDS:
        allowed = {"kind", "path", "lines", "sha256", "symbol"}
        unknown = set(proof) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        lines = proof.get("lines")
        if (
            not isinstance(lines, list)
            or len(lines) != 2
            or any(not isinstance(value, int) for value in lines)
        ):
            raise EvidenceError(f"{label}.lines must be [start, end]")
        start, end = lines
        if start < 1 or end < start or end - start + 1 > MAX_PROOF_LINES:
            raise EvidenceError(f"{label}.lines must select 1-{MAX_PROOF_LINES} lines")
        expected_hash = proof.get("sha256")
        if not isinstance(expected_hash, str) or not SHA256_RE.fullmatch(expected_hash):
            raise EvidenceError(f"{label}.sha256 must be a lowercase SHA-256")
        raw = git_file(repo, implementation, path)
        assert raw is not None
        file_lines = raw.splitlines(keepends=True)
        if end > len(file_lines):
            raise EvidenceError(f"{label}.lines exceeds {path} line count {len(file_lines)}")
        snippet = b"".join(file_lines[start - 1 : end])
        actual_hash = hashlib.sha256(snippet).hexdigest()
        if actual_hash != expected_hash:
            raise EvidenceError(f"{label}.sha256 mismatch for {path}:{start}-{end}")
        symbol = proof.get("symbol")
        if symbol is not None:
            if not isinstance(symbol, str) or not symbol:
                raise EvidenceError(f"{label}.symbol must be a non-empty string")
            if symbol not in snippet.decode("utf-8", errors="replace"):
                raise EvidenceError(f"{label}.symbol not found in cited lines: {symbol}")
        return

    if kind == "json":
        allowed = {"kind", "path", "pointer", "value"}
        unknown = set(proof) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        pointer = require_string(proof, "pointer", label)
        raw = git_file(repo, implementation, path)
        assert raw is not None
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceError(f"{label}: cited file is not valid JSON: {path}") from exc
        actual = json_pointer(data, pointer, label)
        if actual != proof.get("value"):
            raise EvidenceError(f"{label}: JSON value mismatch at {path}{pointer}")
        return

    if kind == "deletion":
        allowed = {"kind", "path"}
        unknown = set(proof) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        if git_file(repo, base, path, required=False) is None:
            raise EvidenceError(f"{label}: deleted file did not exist in base commit: {path}")
        if git_file(repo, implementation, path, required=False) is not None:
            raise EvidenceError(f"{label}: file still exists in implementation commit: {path}")
        return

    raise EvidenceError(f"{label}.kind is unsupported: {kind}")


def validate_deviations(evidence: dict[str, Any], requirement_ids: set[str]) -> dict[str, dict[str, Any]]:
    raw = evidence.get("deviations")
    if not isinstance(raw, list):
        raise EvidenceError("evidence.deviations must be an array")
    result: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(raw, 1):
        label = f"evidence.deviations[{index}]"
        if not isinstance(item, dict):
            raise EvidenceError(f"{label} must be an object")
        allowed = {"id", "kind", "summary", "workaround", "scope_changed", "behavior_changed", "requirements"}
        unknown = set(item) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        deviation_id = require_string(item, "id", label)
        if deviation_id in result:
            raise EvidenceError(f"duplicate deviation id: {deviation_id}")
        require_string(item, "kind", label)
        require_string(item, "summary", label)
        require_string(item, "workaround", label)
        for flag in ("scope_changed", "behavior_changed"):
            if not isinstance(item.get(flag), bool):
                raise EvidenceError(f"{label}.{flag} must be boolean")
            if item[flag]:
                raise EvidenceError(f"{label}.{flag} must be false for accepted evidence")
        affected = item.get("requirements", [])
        if not isinstance(affected, list) or any(not isinstance(value, str) for value in affected):
            raise EvidenceError(f"{label}.requirements must be an array of requirement IDs")
        unknown_requirements = set(affected) - requirement_ids
        if unknown_requirements:
            raise EvidenceError(f"{label} references unknown requirements: {sorted(unknown_requirements)}")
        result[deviation_id] = item
    return result


def validate_evidence(
    repo: Path,
    manifest: dict[str, Any],
    evidence: dict[str, Any],
    implementation: str,
    evidence_directory: Path,
) -> None:
    allowed_top = {"schema_version", "implementation_commit", "requirements", "gates", "deviations"}
    unknown_top = set(evidence) - allowed_top
    if unknown_top:
        raise EvidenceError("evidence.json has unknown top-level fields: " + ", ".join(sorted(unknown_top)))
    if evidence.get("schema_version") != 1:
        raise EvidenceError("evidence.schema_version must be 1")
    if evidence.get("implementation_commit") != implementation:
        raise EvidenceError("evidence.implementation_commit does not match the validated implementation commit")

    target = manifest.get("target")
    if not isinstance(target, dict):
        raise EvidenceError("manifest.target must be an object")
    base = require_sha(str(target.get("base_revision", "")), "manifest.target.base_revision")
    manifest_requirements = indexed_objects(manifest, "requirements")
    requirement_ids = set(manifest_requirements)
    deviations = validate_deviations(evidence, requirement_ids)

    raw_requirements = evidence.get("requirements")
    if not isinstance(raw_requirements, list):
        raise EvidenceError("evidence.requirements must be an array")
    seen_requirements: set[str] = set()
    for index, item in enumerate(raw_requirements, 1):
        label = f"evidence.requirements[{index}]"
        if not isinstance(item, dict):
            raise EvidenceError(f"{label} must be an object")
        allowed = {"id", "status", "proofs", "note", "deviation"}
        unknown = set(item) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        requirement_id = require_string(item, "id", label)
        if requirement_id not in manifest_requirements:
            raise EvidenceError(f"{label} references unknown requirement: {requirement_id}")
        if requirement_id in seen_requirements:
            raise EvidenceError(f"duplicate evidence requirement id: {requirement_id}")
        seen_requirements.add(requirement_id)
        status = item.get("status")
        if status not in REQUIREMENT_STATUSES:
            raise EvidenceError(f"{label}.status must be one of {sorted(REQUIREMENT_STATUSES)}")
        if status == "pass":
            proofs = item.get("proofs")
            if not isinstance(proofs, list) or not proofs:
                raise EvidenceError(f"{label}.proofs must be non-empty for pass")
            for proof_index, proof in enumerate(proofs, 1):
                validate_proof(
                    repo,
                    base,
                    implementation,
                    evidence_directory,
                    proof,
                    f"{label}.proofs[{proof_index}]",
                )
        else:
            note = item.get("note")
            if not isinstance(note, str) or not note:
                raise EvidenceError(f"{label}.note is required for {status}")
            if status == "na" and manifest_requirements[requirement_id].get("allow_na") is True:
                pass
            else:
                deviation_id = item.get("deviation")
                if not isinstance(deviation_id, str) or deviation_id not in deviations:
                    raise EvidenceError(f"{label}.deviation must reference a documented deviation")
                raise EvidenceError(f"requirement {requirement_id} is not fully satisfied: {status}")
    if seen_requirements != requirement_ids:
        missing = sorted(requirement_ids - seen_requirements)
        raise EvidenceError("evidence.requirements is missing IDs: " + ", ".join(missing))

    manifest_gates = indexed_objects(manifest, "gates")
    raw_gates = evidence.get("gates")
    if not isinstance(raw_gates, list):
        raise EvidenceError("evidence.gates must be an array")
    seen_gates: set[str] = set()
    for index, item in enumerate(raw_gates, 1):
        label = f"evidence.gates[{index}]"
        if not isinstance(item, dict):
            raise EvidenceError(f"{label} must be an object")
        allowed = {"id", "status", "exit", "tests", "summary", "run", "job", "url", "note", "deviation"}
        unknown = set(item) - allowed
        if unknown:
            raise EvidenceError(f"{label} has unknown fields: {', '.join(sorted(unknown))}")
        gate_id = require_string(item, "id", label)
        if gate_id not in manifest_gates:
            raise EvidenceError(f"{label} references unknown gate: {gate_id}")
        if gate_id in seen_gates:
            raise EvidenceError(f"duplicate evidence gate id: {gate_id}")
        seen_gates.add(gate_id)
        status = item.get("status")
        if status not in GATE_STATUSES:
            raise EvidenceError(f"{label}.status must be one of {sorted(GATE_STATUSES)}")
        if status != "pass":
            deviation_id = item.get("deviation")
            if not isinstance(deviation_id, str) or deviation_id not in deviations:
                raise EvidenceError(f"{label}.deviation must reference a documented deviation")
            raise EvidenceError(f"required gate {gate_id} did not pass: {status}")
        gate_kind = manifest_gates[gate_id].get("kind", "command")
        if gate_kind == "command":
            if item.get("exit") != 0:
                raise EvidenceError(f"{label}.exit must be 0 for a passed command gate")
        elif gate_kind == "github-actions":
            if not isinstance(item.get("run"), int) or item["run"] <= 0:
                raise EvidenceError(f"{label}.run must be a positive workflow run ID")
            if not isinstance(item.get("url"), str) or not item["url"].startswith("https://github.com/"):
                raise EvidenceError(f"{label}.url must be a GitHub Actions URL")
        elif gate_kind in {"scope", "evidence"}:
            pass
        else:
            raise EvidenceError(f"manifest gate {gate_id} has unsupported kind: {gate_kind}")
    if seen_gates != set(manifest_gates):
        missing = sorted(set(manifest_gates) - seen_gates)
        raise EvidenceError("evidence.gates is missing IDs: " + ", ".join(missing))


def evidence_paths(directory: Path) -> set[str]:
    base = directory.as_posix()
    return {f"{base}/{name}" for name in EVIDENCE_FILES}


def read_worktree_evidence(repo: Path, directory: Path, pack_manifest_raw: bytes) -> dict[str, Any]:
    manifest_path = repo / directory / "manifest.json"
    evidence_path = repo / directory / "evidence.json"
    if not manifest_path.is_file() or not evidence_path.is_file():
        raise EvidenceError("evidence directory must contain manifest.json and evidence.json")
    if manifest_path.read_bytes() != pack_manifest_raw:
        raise EvidenceError("evidence manifest.json is not byte-identical to the patch-pack manifest")
    evidence, _ = load_json_bytes(evidence_path, "evidence.json")
    return evidence


def read_committed_evidence(repo: Path, commit: str, directory: Path, pack_manifest_raw: bytes) -> dict[str, Any]:
    manifest_path = f"{directory.as_posix()}/manifest.json"
    evidence_path = f"{directory.as_posix()}/evidence.json"
    manifest_raw = git_file(repo, commit, manifest_path)
    assert manifest_raw is not None
    if manifest_raw != pack_manifest_raw:
        raise EvidenceError("committed manifest.json is not byte-identical to the patch-pack manifest")
    evidence_raw = git_file(repo, commit, evidence_path)
    assert evidence_raw is not None
    try:
        evidence = json.loads(evidence_raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"invalid committed evidence.json: {exc}") from exc
    if not isinstance(evidence, dict):
        raise EvidenceError("committed evidence.json must contain a JSON object")
    return evidence


def ensure_clean_except(repo: Path, allowed: set[str]) -> None:
    raw = git(repo, "status", "--porcelain=v1", "-z").stdout
    fields = raw.split(b"\0")
    paths: set[str] = set()
    index = 0
    while index < len(fields):
        record = fields[index]
        index += 1
        if not record:
            continue
        text = record.decode("utf-8", errors="strict")
        if len(text) < 4:
            raise EvidenceError(f"unexpected git status record: {text!r}")
        status = text[:2]
        path = text[3:]
        paths.add(path)
        if any(code in status for code in ("R", "C")):
            raise EvidenceError("evidence staging must not contain rename or copy statuses")
    unexpected = paths - allowed
    if unexpected:
        raise EvidenceError("working tree contains non-evidence paths: " + ", ".join(sorted(unexpected)))


def validate_common(pack: Path, repo: Path, implementation: str) -> tuple[dict[str, Any], bytes, Path]:
    if not (repo / ".git").exists():
        raise EvidenceError(f"not a Git repository root: {repo}")
    manifest, raw = load_json_bytes(pack / "manifest.json", "patch-pack manifest.json")
    directory = validate_manifest_identity(manifest)
    require_sha(implementation, "implementation commit")
    target = manifest.get("target")
    if not isinstance(target, dict):
        raise EvidenceError("manifest.target must be an object")
    base = require_sha(str(target.get("base_revision", "")), "manifest.target.base_revision")
    for sha in (base, implementation):
        if git(repo, "cat-file", "-e", f"{sha}^{{commit}}", check=False).returncode != 0:
            raise EvidenceError(f"commit is not available in repository: {sha}")
    assert_scope("implementation", manifest_scope(manifest), diff_scope(repo, base, implementation))
    return manifest, raw, directory


def command_prepare(pack: Path, repo: Path, implementation: str) -> None:
    manifest, raw, directory = validate_common(pack, repo, implementation)
    evidence = read_worktree_evidence(repo, directory, raw)
    validate_evidence(repo, manifest, evidence, implementation, directory)
    expected_paths = evidence_paths(directory)
    ensure_clean_except(repo, expected_paths)
    assert_scope("staged evidence", (expected_paths, set(), set()), diff_scope(repo, "", "", cached=True))
    print(f"PASS: staged JSON evidence for {implementation}")


def command_committed(pack: Path, repo: Path, implementation: str, evidence_commit: str) -> None:
    require_sha(evidence_commit, "evidence commit")
    head = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
    if head != evidence_commit:
        raise EvidenceError(f"repository HEAD is {head}, expected evidence commit {evidence_commit}")
    if git(repo, "status", "--porcelain").stdout.strip():
        raise EvidenceError("working tree must be clean for committed evidence verification")
    manifest, raw, directory = validate_common(pack, repo, implementation)
    parent = git(repo, "rev-parse", f"{evidence_commit}^1").stdout.decode().strip()
    if parent != implementation:
        raise EvidenceError(
            f"evidence commit must directly follow implementation commit: parent={parent}, implementation={implementation}"
        )
    expected_paths = evidence_paths(directory)
    assert_scope("committed evidence", (expected_paths, set(), set()), diff_scope(repo, implementation, evidence_commit))
    evidence = read_committed_evidence(repo, evidence_commit, directory, raw)
    validate_evidence(repo, manifest, evidence, implementation, directory)
    print(f"PASS: committed JSON evidence {evidence_commit} validates implementation {implementation}")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Verify compact committed agent evidence without rerunning project gates.")
    subparsers = result.add_subparsers(dest="mode", required=True)
    for mode in ("prepare", "committed"):
        sub = subparsers.add_parser(mode)
        sub.add_argument("--pack", required=True)
        sub.add_argument("--repo", required=True)
        sub.add_argument("--implementation-commit", required=True)
        if mode == "committed":
            sub.add_argument("--evidence-commit", default="HEAD")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    pack = Path(args.pack).resolve()
    repo = Path(args.repo).resolve()
    try:
        implementation = require_sha(args.implementation_commit, "implementation commit")
        if args.mode == "prepare":
            command_prepare(pack, repo, implementation)
        else:
            evidence = args.evidence_commit
            if evidence == "HEAD":
                evidence = git(repo, "rev-parse", "HEAD").stdout.decode().strip()
            command_committed(pack, repo, implementation, require_sha(evidence, "evidence commit"))
    except EvidenceError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
