#!/usr/bin/env python3
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from gpt_patch_pack_v1_common import load_json as load_strict_json

class EvidenceError(RuntimeError):
    pass

def git(repo: Path,*args: str) -> str:
    proc=subprocess.run(["git","-C",str(repo),*args],text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if proc.returncode:
        raise EvidenceError(proc.stderr.strip() or proc.stdout.strip())
    return proc.stdout.strip()

def load(path: Path) -> tuple[dict,bytes]:
    raw=path.read_bytes()
    value=load_strict_json(path)
    if not isinstance(value,dict):
        raise EvidenceError(f"{path} must contain an object")
    return value,raw

def scope(repo: Path,base: str,head: str) -> tuple[set[str],set[str],set[str]]:
    raw=subprocess.check_output(["git","-C",str(repo),"diff","--name-status","-z","--find-renames","--find-copies",f"{base}..{head}","--"])
    fields=raw.split(b"\0"); created=set(); modified=set(); deleted=set(); i=0
    while i<len(fields):
        status_raw=fields[i]; i+=1
        if not status_raw: continue
        status=status_raw.decode(); path=fields[i].decode(); i+=1
        if status[0] in {"R","C"}:
            new=fields[i].decode(); i+=1
            if status[0]=="R": deleted.add(path)
            created.add(new)
        elif status[0]=="A": created.add(path)
        elif status[0] in {"M","T"}: modified.add(path)
        elif status[0]=="D": deleted.add(path)
        else: raise EvidenceError(f"unsupported status {status}")
    return created,modified,deleted

def git_file(repo: Path,commit: str,path: str,required: bool=True) -> bytes|None:
    proc=subprocess.run(["git","-C",str(repo),"show",f"{commit}:{path}"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if proc.returncode:
        if required: raise EvidenceError(f"missing {path} at {commit}")
        return None
    return proc.stdout

def validate_proof(repo: Path,base: str,implementation: str,proof: dict) -> None:
    kind=proof.get("kind"); path=proof.get("path")
    if "/evidence/" in path or path.endswith("/evidence.json") or path.endswith("/manifest.json"):
        raise EvidenceError("must not cite evidence files")
    if kind in {"source","test","workflow","documentation"}:
        lines=proof.get("lines"); expected=proof.get("sha256")
        if not isinstance(lines,list) or len(lines)!=2 or not isinstance(expected,str):
            raise EvidenceError("invalid text proof")
        raw=git_file(repo,implementation,path); start,end=lines
        selected=b"".join(raw.splitlines(keepends=True)[start-1:end])
        if hashlib.sha256(selected).hexdigest()!=expected:
            raise EvidenceError(f"sha256 mismatch: {path}")
        if proof.get("symbol") and proof["symbol"] not in selected.decode(errors="replace"):
            raise EvidenceError(f"proof symbol mismatch: {path}")
    elif kind=="deletion":
        if git_file(repo,base,path,False) is None or git_file(repo,implementation,path,False) is not None:
            raise EvidenceError(f"deletion proof mismatch: {path}")
    elif kind=="json":
        raw=git_file(repo,implementation,path)
        value=json.loads(raw.decode())
        for part in proof["pointer"].lstrip("/").split("/"):
            value=value[part]
        if value!=proof.get("value"):
            raise EvidenceError(f"JSON proof mismatch: {path}")
    else:
        raise EvidenceError(f"unsupported proof kind: {kind}")

def validate(repo: Path,manifest: dict,evidence: dict,implementation: str) -> None:
    allowed_evidence = {"schema_version", "implementation_commit", "compatibility_scope", "compatibility_authorized", "compatibility_features_added", "legacy_paths_added", "fallbacks_added", "migration_behavior_added", "requirements", "gates", "deviations"}
    unknown = set(evidence) - allowed_evidence
    if unknown:
        raise EvidenceError(f"unknown top-level fields: {sorted(unknown)}")
    if manifest.get("format")!="gpt-patch-pack-v1":
        raise EvidenceError("manifest is not GPT Patch Pack v1")
    base=manifest["target"]["base_revision"]
    expected=(set(manifest["files_created"]),set(manifest["files_modified"]),set(manifest["files_deleted"]))
    if scope(repo,base,implementation)!=expected:
        raise EvidenceError("implementation scope mismatch")
    if evidence.get("implementation_commit")!=implementation:
        raise EvidenceError("implementation commit mismatch")
    required_compat={
        "compatibility_scope":"none","compatibility_authorized":False,
        "compatibility_features_added":[],"legacy_paths_added":[],
        "fallbacks_added":[],"migration_behavior_added":[],
    }
    for key,value in required_compat.items():
        if evidence.get(key)!=value:
            raise EvidenceError(f"compatibility evidence mismatch: {key}")
    manifest_requirements=[item["id"] for item in manifest["requirements"]]
    evidence_requirements=evidence.get("requirements")
    if [item.get("id") for item in evidence_requirements]!=manifest_requirements:
        raise EvidenceError("missing IDs or requirement IDs mismatch")
    deviations = evidence.get("deviations")
    if not isinstance(deviations, list):
        raise EvidenceError("deviations must be an array")
    for deviation in deviations:
        if not isinstance(deviation, dict) or not deviation.get("id") or not deviation.get("summary"):
            raise EvidenceError("invalid structured deviation")
    for item in evidence_requirements:
        if item.get("status")!="pass" or not item.get("proofs"):
            raise EvidenceError(f"requirement did not pass: {item.get('id')}")
        for proof in item["proofs"]:
            validate_proof(repo,base,implementation,proof)
    if [item.get("id") for item in evidence.get("gates",[])]!=[item["id"] for item in manifest["gates"]]:
        raise EvidenceError("gate IDs mismatch")
    gate_kinds = {item["id"]: item.get("kind") for item in manifest["gates"]}
    gate_heads = {item["id"]: item.get("head") for item in manifest["gates"]}
    for gate in evidence["gates"]:
        if gate_heads.get(gate.get("id")) == "evidence":
            raise EvidenceError("evidence-head CI is external metadata")
        if gate.get("status")!="pass":
            raise EvidenceError(f"gate did not pass: {gate.get('id')}")
        if gate_kinds.get(gate.get("id")) == "command" and gate.get("exit") != 0:
            raise EvidenceError(f"gate did not pass: {gate.get('id')}")

def main() -> int:
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="mode",required=True)
    for mode in ("prepare","committed"):
        command=sub.add_parser(mode)
        command.add_argument("--pack",required=True,type=Path)
        command.add_argument("--repo",required=True,type=Path)
        command.add_argument("--implementation-commit",required=True)
        if mode=="committed": command.add_argument("--evidence-commit",required=True)
    args=parser.parse_args()
    pack=args.pack.resolve(); repo=args.repo.resolve()
    manifest_path = pack / "MANIFEST.json"
    if not manifest_path.exists():
        manifest_path = pack / "manifest.json"
    manifest,manifest_raw=load(manifest_path)
    evidence_dir=Path(manifest["evidence_directory"])
    if args.mode=="prepare":
        manifest_path=repo/evidence_dir/"manifest.json"; evidence_path=repo/evidence_dir/"evidence.json"
        if manifest_path.read_bytes()!=manifest_raw:
            raise EvidenceError("prepared manifest is not byte-identical")
        evidence,_=load(evidence_path)
        validate(repo,manifest,evidence,args.implementation_commit)
    else:
        evidence_commit=args.evidence_commit
        if git(repo,"rev-parse","HEAD")!=evidence_commit or git(repo,"rev-parse",f"{evidence_commit}^")!=args.implementation_commit:
            raise EvidenceError("evidence commit ancestry mismatch")
        expected={f"{evidence_dir}/manifest.json",f"{evidence_dir}/evidence.json"}
        actual=set(git(repo,"diff","--name-only",f"{args.implementation_commit}..{evidence_commit}","--").splitlines())
        if actual!=expected:
            raise EvidenceError("evidence-only scope mismatch")
        committed_manifest=git_file(repo,evidence_commit,f"{evidence_dir}/manifest.json")
        if committed_manifest!=manifest_raw:
            raise EvidenceError("committed manifest is not byte-identical")
        evidence=json.loads(git_file(repo,evidence_commit,f"{evidence_dir}/evidence.json").decode())
        validate(repo,manifest,evidence,args.implementation_commit)
    print(f"PASS: {args.mode} GPT Patch Pack v1 evidence")
    return 0

if __name__=="__main__":
    try: raise SystemExit(main())
    except (EvidenceError,OSError,json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}",file=sys.stderr); raise SystemExit(1)
