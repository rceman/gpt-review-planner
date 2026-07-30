#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gpt_patch_pack_v1_common import load_json as load_strict_json, validate_manifest, validate_compatibility

def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(5)

def load(path: Path) -> dict:
    try:
        value=load_strict_json(path)
    except Exception as exc:
        fail(f"invalid JSON {path}: {exc}")
    if not isinstance(value,dict):
        fail(f"{path} must contain an object")
    return value

def proof(repo: Path, commit: str, item: dict) -> dict:
    kind=item.get("kind")
    path=item.get("path")
    if kind in {"json","deletion"}:
        return dict(item)
    lines=item.get("lines")
    if not isinstance(lines,list) or len(lines)!=2:
        fail("text proof requires lines")
    start,end=lines
    raw=subprocess.check_output(["git","-C",str(repo),"show",f"{commit}:{path}"])
    selected=b"".join(raw.splitlines(keepends=True)[start-1:end])
    result=dict(item)
    result["sha256"]=hashlib.sha256(selected).hexdigest()
    return result

def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",required=True,type=Path)
    parser.add_argument("--manifest",required=True,type=Path)
    parser.add_argument("--evidence-plan",required=True,type=Path)
    parser.add_argument("--gate-run",required=True,type=Path)
    parser.add_argument("--implementation-commit",required=True)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    repo=args.repo.resolve()
    manifest=load(args.manifest)
    plan=load(args.evidence_plan)
    gate_run=load(args.gate_run)
    implementation=args.implementation_commit
    if subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()!=implementation:
        fail("HEAD mismatch")
    try:
        validate_manifest(manifest)
        validate_compatibility(manifest["compatibility"])
    except ValueError as exc:
        fail(f"manifest validation failed: {exc}")
    if gate_run.get("implementation_commit")!=implementation or gate_run.get("status")!="pass":
        fail("gate run identity or status mismatch")
    manifest_ids=[item["id"] for item in manifest.get("requirements",[])]
    planned=plan.get("requirements")
    if not isinstance(planned,list) or [item.get("id") for item in planned]!=manifest_ids:
        fail("evidence requirement order mismatch")
    gates=gate_run.get("gates")
    if [item.get("id") for item in gates]!=[item["id"] for item in manifest.get("gates",[])]:
        fail("gate order mismatch")
    captured={group.get("id"):group for group in gates}
    captured.update({step.get("id"):step for group in gates for step in group.get("steps",[])})
    for gate in manifest["gates"]:
        step=captured.get(gate["id"])
        if step is None or step.get("status")!="pass" or step.get("exit")!=0:
            fail(f"gate was not captured successfully: {gate['id']}")
        for key in ("argv","env","timeout_seconds","max_output_bytes"):
            if step.get(key)!=gate.get(key): fail(f"captured gate does not match manifest: {gate['id']}/{key}")
    declaration=manifest.get("compatibility",{})
    if declaration.get("authorized") is False:
        for key in ("compatibility_features_added","legacy_paths_added","fallbacks_added","migration_behavior_added"):
            if plan.get(key,[])!=[]: fail(f"unauthorized compatibility evidence: {key}")
    result={
        "schema_version":1,
        "implementation_commit":implementation,
        "requirements":[
            {
                **{k:item[k] for k in ("id","status","note","deviation") if k in item},
                "proofs":[proof(repo,implementation,p) for p in item.get("proofs",[])],
            }
            for item in planned
        ],
        "gates":[
            {k:item[k] for k in ("id","status","exit","summary","tests","metrics") if k in item}
            for item in gates
        ],
        "deviations":plan.get("deviations",[]),
        "compatibility_scope":declaration["scope"],
        "compatibility_authorized":declaration["authorized"],
        "compatibility_features_added":plan.get("compatibility_features_added",[]),
        "legacy_paths_added":plan.get("legacy_paths_added",[]),
        "fallbacks_added":plan.get("fallbacks_added",[]),
        "migration_behavior_added":plan.get("migration_behavior_added",[]),
    }
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():
        fail("output already exists")
    args.output.write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    print(f"Evidence generated: {args.output}")

if __name__=="__main__":
    main()
