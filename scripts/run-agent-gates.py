#!/usr/bin/env python3
"""Execute a validated, repository-relative gate plan and emit gate-run.json."""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_gate_contract import (  # noqa: E402
    TaskGateContractError,
    contract_identity,
    gate_plan,
    load_json as load_contract_json,
    validate_contract,
)

PARSERS = {"exit", "unittest", "pytest"}
SHA = re.compile(r"^[0-9a-f]{40}$")

def fail(message):
    if str(message).startswith("TASK_GATE_CONTRACT_MISMATCH:"):
        print(message, file=sys.stderr)
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    raise SystemExit(5)

def load_plan(path, contract_path):
    try: data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc: fail(f"invalid gate plan: {exc}")
    if data.get("schema_version") != 1 or not isinstance(data.get("gates"), list): fail("invalid gate plan schema")
    ids=set(); mids=set(); metrics=set()
    for gate in data["gates"]:
        if gate.get("id") in ids: fail("duplicate gate ID")
        ids.add(gate.get("id"))
        for step in gate.get("steps", []):
            if step.get("id") in mids: fail("duplicate step ID")
            mids.add(step.get("id"))
            if step.get("parser") not in PARSERS: fail("unknown parser")
            if step["parser"] == "exit" and step.get("metric") is not None: fail("exit parser must not declare metric")
            if step["parser"] != "exit" and not isinstance(step.get("metric"), str): fail("test parser requires metric")
            if step.get("metric"):
                if step["metric"] in metrics: fail("duplicate metric ID")
                metrics.add(step["metric"])
            if not isinstance(step.get("timeout_seconds"), int) or step["timeout_seconds"] <= 0: fail("invalid timeout")
            cwd=step.get("cwd")
            if cwd and (os.path.isabs(cwd) or any(part == ".." for part in Path(cwd).parts)): fail("invalid cwd")
            if not isinstance(step.get("argv"), list) or any(not isinstance(x,str) for x in step["argv"]): fail("invalid argv")
            if step["argv"] and step["argv"][0] in {"true", "false", "echo"}: fail("placeholder gate command")
            if any(any(c in x for c in ";&|<>$") for x in step["argv"]): fail("shell strings are not allowed")
    try:
        contract = validate_contract(load_contract_json(Path(contract_path)))
        if data != gate_plan(contract):
            fail("TASK_GATE_CONTRACT_MISMATCH: executable gate plan diverges from contract")
        return data, contract
    except TaskGateContractError as exc:
        fail(f"TASK_GATE_CONTRACT_MISMATCH: {exc}")

def count_output(parser, out):
    if parser == "exit": return None
    if parser == "unittest":
        m=re.search(r"Ran\s+(\d+)\s+tests?", out)
    else:
        m=re.search(r"(\d+)\s+passed(?:\s+in\s+[^\n]+)?", out)
    if not m: raise ValueError("expected test count not found")
    return int(m.group(1))

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",required=True); ap.add_argument("--plan",required=True); ap.add_argument("--task-gate-contract",required=True); ap.add_argument("--implementation-commit",required=True); ap.add_argument("--output-dir",required=True); a=ap.parse_args()
    if not SHA.fullmatch(a.implementation_commit): fail("implementation commit must be a lowercase 40-character SHA")
    repo=Path(a.repo).resolve(); plan, contract=load_plan(Path(a.plan), a.task_gate_contract)
    if subprocess.run(["git","-C",str(repo),"cat-file","-e",a.implementation_commit+"^{commit}"]).returncode: fail("implementation commit does not exist")
    if subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()!=a.implementation_commit: fail("HEAD does not equal implementation commit")
    dirty=subprocess.check_output(["git","-C",str(repo),"status","--porcelain"],text=True)
    allowed={str(Path(a.output_dir).resolve()), str(Path(a.output_dir).resolve().parent / "manifest.json")}
    if any(line[3:].strip() not in allowed for line in dirty.splitlines()): fail("worktree must be clean except intended evidence files")
    outdir=Path(a.output_dir).resolve()
    if outdir == repo or repo in outdir.parents: fail("output directory must be outside repository")
    for gate in plan["gates"]:
        for step in gate["steps"]:
            candidate=(repo/step.get("cwd", "")).resolve()
            if repo not in candidate.parents and candidate != repo: fail("cwd escapes repository")
    outdir.mkdir(parents=True,exist_ok=True); started=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'); results=[]; overall="pass"
    for gate in plan["gates"]:
        gr={"id":gate["id"],"status":"pass","exit":0,"metrics":{},"steps":[]}
        for step in gate["steps"]:
            t=time.monotonic(); stdout=b""; stderr=b""; code=0; status="pass"; diagnostic=""
            try:
                env=os.environ.copy(); env.update(step.get("env", {}))
                p=subprocess.run(step["argv"],cwd=repo/step.get("cwd", ""),env=env,capture_output=True,timeout=step["timeout_seconds"])
                stdout,stderr,code=p.stdout,p.stderr,p.returncode
                count=count_output(step["parser"],stdout.decode(errors="replace")+stderr.decode(errors="replace"))
                if count is not None: gr["metrics"][step["metric"]]=count
                if code: status="fail"
            except subprocess.TimeoutExpired as exc: stdout=exc.stdout or b""; stderr=exc.stderr or b""; code=124; status="fail"; diagnostic="timeout"
            except ValueError as exc: code=1; status="fail"; diagnostic=str(exc)
            item={"id":step["id"],"argv":step["argv"],"env":step.get("env",{}),"cwd":step.get("cwd", ""),"parser":step["parser"],"metric":step.get("metric"),"timeout_seconds":step["timeout_seconds"],"max_output_bytes":step.get("max_output_bytes",16777216),"status":status,"exit":code,"duration_ms":round((time.monotonic()-t)*1000),"stdout_sha256":hashlib.sha256(stdout).hexdigest(),"stderr_sha256":hashlib.sha256(stderr).hexdigest()}
            if diagnostic: item["message"]=diagnostic
            gr["steps"].append(item)
            if len(gate.get("steps", [])) == 1:
                for key in ("argv", "env", "timeout_seconds", "max_output_bytes"):
                    if key in item: gr[key] = item[key]
            (outdir/f"{step['id']}.stdout").write_bytes(stdout); (outdir/f"{step['id']}.stderr").write_bytes(stderr)
            if status != "pass": gr["status"]="fail"; gr["exit"]=code; overall="fail"; break
        results.append(gr)
        if overall != "pass": break
    result={"schema_version":1,"implementation_commit":a.implementation_commit,"started_at":started,"completed_at":datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),"status":overall,"gates":results}
    result["task_gate_contract"]=contract_identity(contract)
    target=outdir/"gate-run.json"; fd,tmp=tempfile.mkstemp(dir=outdir); os.close(fd); Path(tmp).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8"); os.replace(tmp,target)
    print(f"Gate run: {overall} | sha={a.implementation_commit} | gates={len(results)}")
    raise SystemExit(0 if overall=="pass" else 1)
if __name__ == "__main__": main()
