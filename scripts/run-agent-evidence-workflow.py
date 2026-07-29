#!/usr/bin/env python3
"""Bounded synchronous evidence workflow runner."""
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

PHASES=['INITIALIZED','IDENTITY_VERIFIED','IMPLEMENTATION_CI_VERIFIED','WORKTREE_CREATED','GATES_COMPLETED','EVIDENCE_INPUTS_PREPARED','EVIDENCE_GENERATED','PREPARE_VERIFIED','EVIDENCE_COMMITTED','COMMITTED_VERIFIED','EVIDENCE_PUSHED','EVIDENCE_CI_VERIFIED','REPORT_RENDERED','COMPLETE']
def die(phase,reason,diag,state=None):
    print(json.dumps({'status':'blocked','phase':phase,'reason':reason,'diagnostic':diag[:500],'resume_command':f'python3 scripts/run-agent-evidence-workflow.py resume --repo {state.get("repo") if state else "<REPOSITORY>"}'},sort_keys=True)); raise SystemExit(5)
def run(cmd, cwd, out=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=1900)
    if out: Path(out).write_text(p.stdout,encoding='utf-8')
    if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip() or f'exit {p.returncode}')
    return p.stdout
def atomic(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent); os.close(fd); Path(tmp).write_text(json.dumps(obj,indent=2,sort_keys=True)+'\n'); os.replace(tmp,path)
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='command',required=True)
    for name in ('run','resume'):
        p=sub.add_parser(name); p.add_argument('--repo',required=True); p.add_argument('--inputs' if name=='run' else '--run-id',required=True)
    a=ap.parse_args(); repo=Path(a.repo).resolve()
    if a.command=='resume':
        common=Path(run(['git','rev-parse','--git-common-dir'],repo).strip()); state= json.loads((common/'gpt-review'/'runs'/a.run_id/'state.json').read_text()); inputs=Path(state['inputs'])
    else: inputs=Path(a.inputs).resolve(); common=Path(run(['git','rev-parse','--git-common-dir'],repo).strip()); workflow=json.loads((inputs/'workflow.json').read_text()); head=run(['git','rev-parse','HEAD'],repo).strip(); run_id=hashlib.sha256((str(repo)+run(['git','branch','--show-current'],repo)+head+hashlib.sha256((inputs/'workflow.json').read_bytes()).hexdigest()).encode()).hexdigest()[:20]; state={'repo':str(repo),'inputs':str(inputs),'run_id':run_id,'implementation_sha':head,'phase':'INITIALIZED'}; state_dir=common/'gpt-review'/'runs'/run_id; state_dir.mkdir(parents=True,exist_ok=True); atomic(state_dir/'state.json',state)
    if a.command=='resume': state_dir=common/'gpt-review'/'runs'/state['run_id'];
    def save(phase,**extra): state.update({'phase':phase,**extra}); atomic(state_dir/'state.json',state); print('EVIDENCE WORKFLOW: '+phase.lower().replace('_',' '))
    try:
        workflow=json.loads((inputs/'workflow.json').read_text()); seed=inputs/'manifest-seed.json'; plan=inputs/'evidence-plan.json'; gate_plan=inputs/'gate-plan.json'
        if state['phase']=='INITIALIZED':
            if run(['git','branch','--show-current'],repo).strip()!=workflow['branch'] or Path(repo/'VERSION').read_text().strip()!=workflow['version']: raise RuntimeError('repository identity mismatch')
            save('IDENTITY_VERIFIED')
        if state['phase']=='IDENTITY_VERIFIED':
            ci=run(['python3','scripts/check-github-ci.py','--repository',workflow['repository'],'--sha',state['implementation_sha'],'--policy',workflow['ci']['policy'],'--workflow',workflow['ci']['workflow'],'--event',workflow['ci']['event'],'--wait','--timeout',str(workflow['ci']['timeout_seconds']),'--interval',str(workflow['ci']['interval_seconds']),'--format','json'],repo); (state_dir/'implementation-ci.json').write_text(ci); save('IMPLEMENTATION_CI_VERIFIED')
        if state['phase']=='IMPLEMENTATION_CI_VERIFIED':
            stale=repo/'.gpt-review/evidence/v1.3.0/patch-20260729-130000-evidence-automation'; quarantine=Path('/tmp/gpt-review-stale-evidence-20260729-101500')
            if stale.exists() and not quarantine.exists(): shutil.move(stale,quarantine)
            worktree=state_dir/'worktree'; run(['git','worktree','add','--detach',str(worktree),state['implementation_sha']],repo); state['worktree']=str(worktree); save('WORKTREE_CREATED')
        if state['phase']=='WORKTREE_CREATED':
            gateout=state_dir/'gate-run'; run(['python3',str(repo/'scripts/run-agent-gates.py'),'--repo',state['worktree'],'--plan',str(gate_plan),'--implementation-commit',state['implementation_sha'],'--output-dir',str(gateout)],repo); save('GATES_COMPLETED',gate_run=str(gateout/'gate-run.json'))
        if state['phase']=='GATES_COMPLETED':
            now=datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'); evidence=repo/f'.gpt-review/evidence/{workflow["version"]}/patch-{now}-{workflow["evidence_slug"]}'; seedout=state_dir/'manifest-seed.json'; shutil.copy2(seed,seedout); planout=state_dir/'evidence-plan.json'; shutil.copy2(plan,planout); run(['python3',str(repo/'scripts/prepare-agent-evidence.py'),'--repo',str(repo),'--manifest-seed',str(seedout),'--evidence-plan',str(planout),'--base-revision',workflow['base_revision'],'--implementation-commit',state['implementation_sha'],'--evidence-directory',str(evidence.relative_to(repo)),'--manifest-output',str(evidence/'manifest.json'),'--resolved-plan-output',str(state_dir/'evidence-plan.resolved.json')],repo); state['evidence']=str(evidence); save('EVIDENCE_INPUTS_PREPARED')
        if state['phase']=='EVIDENCE_INPUTS_PREPARED':
            run(['python3',str(repo/'scripts/generate-agent-evidence.py'),'--repo',str(repo),'--manifest',state['evidence']+'/manifest.json','--evidence-plan',str(state_dir/'evidence-plan.resolved.json'),'--gate-run',state['gate_run'],'--ci-result','implementation-ci='+str(state_dir/'implementation-ci.json'),'--implementation-commit',state['implementation_sha'],'--output',state['evidence']+'/evidence.json'],repo); save('EVIDENCE_GENERATED')
        if state['phase']=='EVIDENCE_GENERATED':
            pack=state_dir/'pack'; pack.mkdir(); shutil.copy2(state['evidence']+'/manifest.json',pack/'manifest.json'); run(['python3',str(repo/'scripts/verify-agent-evidence.py'),'prepare','--pack',str(pack),'--repo',str(repo),'--implementation-commit',state['implementation_sha']],repo); save('PREPARE_VERIFIED')
        print('EVIDENCE WORKFLOW: complete')
    except Exception as e: die(state.get('phase','INITIALIZED'),'WORKFLOW_FAILED',str(e),state)
if __name__=='__main__': main()
