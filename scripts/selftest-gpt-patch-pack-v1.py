#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json
from pathlib import Path
import subprocess,tempfile

def run(argv,cwd):
 p=subprocess.run(argv,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 if p.returncode: raise RuntimeError(p.stderr or p.stdout)
 return p.stdout

def git(repo,*args): return run(["git",*args],repo).strip()

def main():
 planner=Path(__file__).resolve().parents[1]
 with tempfile.TemporaryDirectory(prefix="gpt-pack-v1-selftest-") as raw:
  root=Path(raw); remote=root/"remote.git"; repo=root/"repo"; author=root/"author"; out=root/"out"
  run(["git","init","--bare",str(remote)],root)
  run(["git","clone",str(remote),str(repo)],root)
  git(repo,"config","user.name","selftest"); git(repo,"config","user.email","selftest@example.invalid"); git(repo,"switch","-c","main")
  (repo/"README.md").write_text("before\n"); (repo/"obsolete.txt").write_text("remove\n")
  git(repo,"add","--all"); git(repo,"commit","-m","base"); git(repo,"push","-u","origin","main")
  base=git(repo,"rev-parse","HEAD")
  run(["git","clone","--branch","main",str(remote),str(author)],root)
  (author/"README.md").write_text("after\n"); (author/"new.txt").write_text("new\n"); (author/"obsolete.txt").unlink()
  git(author,"add","--all")
  patch=root/"changes.patch"; patch.write_text(run(["git","diff","--cached","--binary","--full-index","HEAD","--"],author))
  task=root/"AGENT_TASK.md"; task.write_text("# AGENT_TASK\nCompatibility scope: none\nCompatibility authorization: not granted\nCanonical implementation: fixture\nLegacy behavior: unsupported and out of scope\n")
  requirements=root/"requirements.json"; requirements.write_text(json.dumps({"requirements":[{"id":"REQ-001","summary":"Apply","acceptance":["Exact tree."]}]})+"\n")
  gates=root/"gates.json"; gates.write_text(json.dumps({"gates":[{"id":"diff-check","name":"Diff check","kind":"command","argv":["git","diff","--cached","--check"],"env":{},"timeout_seconds":60,"max_output_bytes":1048576}]})+"\n")
  build=run(["python3",str(planner/"scripts/build-gpt-patch-pack-v1.py"),"--repo",str(repo),"--repository","selftest/repo","--accepted-origin-url",str(remote),"--branch","main","--base-commit",base,"--remote","origin","--remote-ref","refs/remotes/origin/main","--baseline-release","v1.3.0","--slug","synthetic","--title","Synthetic pack","--description","Synthetic test","--changes-patch",str(patch),"--agent-task",str(task),"--requirements",str(requirements),"--gates",str(gates),"--output-directory",str(out),"--planner-commit","f8cb8bc67c138f7e0e026c9270d3bd89dcd855d1"],planner)
  archives=list(out.glob("patch-*-synthetic.tar.gz"))
  if len(archives)!=1: raise RuntimeError("archive not built")
  archive=archives[0]; digest=hashlib.sha256(archive.read_bytes()).hexdigest()
  if git(repo,"status","--porcelain=v1","--untracked-files=all"): raise RuntimeError("verify-only changed repo")
  applied=run(["python3",str(planner/"scripts/gpt-patch-pack-runner-v1.py"),"--archive",str(archive),"--archive-sha256",digest,"--repo",str(repo),"--apply"],planner)
  if "PACK_VERIFIED" not in applied or "GPT_PATCH_PACK_APPLIED" not in applied: raise RuntimeError("markers missing")
  if (repo/"README.md").read_text()!="after\n" or not (repo/"new.txt").is_file() or (repo/"obsolete.txt").exists(): raise RuntimeError("result mismatch")
  print(f"GPT_PATCH_PACK_V1_SELFTEST_OK base={base} archive_sha256={digest}")
if __name__=="__main__": main()
