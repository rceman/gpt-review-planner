#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re, sys
from pathlib import Path
from typing import Any

SHA_RE=re.compile(r"^[0-9a-f]{40}$")
SLUG_RE=re.compile(r"^[a-z0-9][a-z0-9_-]{0,79}$")
ALLOWED={"schema_version","task_id","status","implementation_commit","evidence_commit","summary","details","gates","deviations","next_action"}
STATUSES={"succeeded","needs_gpt_revision","failed"}

class DuplicateKeyError(ValueError): pass

def strict_object(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise DuplicateKeyError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def error(errors, code, message): errors.append({"code":code,"message":message})

def load(path:Path, errors:list[dict[str,str]]):
    try:
        info=path.lstat()
        if not path.is_file() or path.is_symlink():
            error(errors,"invalid_file","result must be a regular non-symlink file"); return None
        if info.st_size<=0 or info.st_size>1024*1024:
            error(errors,"invalid_size","result must contain 1 to 1048576 bytes"); return None
        return json.loads(path.read_text(encoding="utf-8"),object_pairs_hook=strict_object)
    except (OSError,UnicodeDecodeError,json.JSONDecodeError,DuplicateKeyError) as exc:
        error(errors,"invalid_json",str(exc)); return None

def validate(path:Path, task_id:str, manifest_path:Path|None):
    errors=[]; value=load(path,errors)
    if not isinstance(value,dict):
        if value is not None: error(errors,"invalid_root","result root must be an object")
        return errors
    for key in sorted(set(value)-ALLOWED): error(errors,"unknown_field",f"unknown field: {key}")
    if value.get("schema_version")!=2: error(errors,"invalid_schema","schema_version must be 2")
    if value.get("task_id")!=task_id or not SLUG_RE.fullmatch(str(value.get("task_id",''))): error(errors,"task_id_mismatch","task_id must equal the gateway task ID")
    status=value.get("status")
    if status not in STATUSES: error(errors,"invalid_status","status must be succeeded, needs_gpt_revision, or failed")
    summary=value.get("summary")
    if not isinstance(summary,str) or not summary.strip() or len(summary.encode())>4096: error(errors,"invalid_summary","summary must contain 1 to 4096 UTF-8 bytes")
    details=value.get("details")
    if not isinstance(details,list) or len(details)>64 or any(not isinstance(x,str) or not x.strip() or len(x.encode())>2048 for x in details): error(errors,"invalid_details","details must be an array of up to 64 bounded non-empty strings")
    gates=value.get("gates")
    gate_ids=[]
    if not isinstance(gates,list) or len(gates)>128: error(errors,"invalid_gates","gates must be an array of up to 128 entries")
    else:
        for i,item in enumerate(gates):
            if not isinstance(item,dict) or set(item)!={"id","status","exit","summary"}: error(errors,"invalid_gate",f"gates[{i}] has invalid fields"); continue
            if not isinstance(item["id"],str) or not item["id"] or item["id"] in gate_ids: error(errors,"invalid_gate_id",f"gates[{i}].id is empty or duplicate")
            gate_ids.append(item["id"])
            if item["status"] not in {"pass","fail","not_run"} or not isinstance(item["exit"],int) or not isinstance(item["summary"],str) or not item["summary"].strip(): error(errors,"invalid_gate",f"gates[{i}] has invalid status, exit, or summary")
    deviations=value.get("deviations")
    if not isinstance(deviations,list) or len(deviations)>64: error(errors,"invalid_deviations","deviations must be an array of up to 64 entries")
    else:
        expected={"id","kind","summary","workaround","scope_changed","behavior_changed","requirements"}
        for i,item in enumerate(deviations):
            if not isinstance(item,dict) or set(item)!=expected: error(errors,"invalid_deviation",f"deviations[{i}] has invalid fields"); continue
            if item["behavior_changed"] is not False: error(errors,"behavior_change_forbidden",f"deviations[{i}].behavior_changed must be false")
            if not isinstance(item["scope_changed"],bool) or not isinstance(item["requirements"],list): error(errors,"invalid_deviation",f"deviations[{i}] has invalid types")
    for field in ("implementation_commit","evidence_commit"):
        if field in value and not SHA_RE.fullmatch(str(value[field])): error(errors,"invalid_commit",f"{field} must be a lowercase 40-character SHA")
    if status=="succeeded":
        for field in ("implementation_commit","evidence_commit"):
            if field not in value: error(errors,"missing_commit",f"succeeded requires {field}")
        if not gates: error(errors,"missing_gates","succeeded requires gate results")
        for item in gates if isinstance(gates,list) else []:
            if isinstance(item,dict) and (item.get("status")!="pass" or item.get("exit")!=0): error(errors,"gate_not_passed",f"gate {item.get('id')} did not pass")
    if status=="needs_gpt_revision" and (not isinstance(value.get("next_action"),str) or not value["next_action"].strip()): error(errors,"missing_next_action","needs_gpt_revision requires next_action")
    if manifest_path:
        try: manifest=json.loads(manifest_path.read_text(encoding="utf-8"),object_pairs_hook=strict_object)
        except Exception as exc: error(errors,"invalid_manifest",str(exc)); manifest=None
        if isinstance(manifest,dict):
            expected=[g.get("id") for g in manifest.get("gates",[]) if isinstance(g,dict)]
            if status=="succeeded" and gate_ids!=expected: error(errors,"gate_identity_mismatch","successful result gates must exactly match manifest order")
    return errors

def main(argv=None):
    p=argparse.ArgumentParser(description="Validate one gateway agent-result.json file.")
    p.add_argument("--result",required=True,type=Path); p.add_argument("--task-id",required=True); p.add_argument("--manifest",type=Path); p.add_argument("--format",choices=("text","json"),default="text")
    a=p.parse_args(argv); errors=validate(a.result,a.task_id,a.manifest); doc={"schema_version":1,"valid":not errors,"task_id":a.task_id,"errors":errors}
    if a.format=="json": print(json.dumps(doc,sort_keys=True,separators=(",",":")))
    elif errors:
        for item in errors: print(f"ERROR [{item['code']}]: {item['message']}",file=sys.stderr)
    else: print(f"PASS: {a.result}")
    return 0 if not errors else 1
if __name__=="__main__": raise SystemExit(main())
