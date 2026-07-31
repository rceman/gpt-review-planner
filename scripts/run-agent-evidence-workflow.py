#!/usr/bin/env python3
"""Run the bounded evidence workflow with durable, resumable phase state."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from task_gate_contract import (  # noqa: E402
    TaskGateContractError,
    atomic_write,
    load_json as load_contract_json,
    validate_contract,
)
from execution_mode import require_repository_evidence  # noqa: E402

PHASES = ['INITIALIZED','IDENTITY_VERIFIED','IMPLEMENTATION_CI_VERIFIED','WORKTREE_CREATED','TASK_GATE_CONTRACT_VERIFIED','GATES_COMPLETED','EVIDENCE_INPUTS_PREPARED','EVIDENCE_GENERATED','PREPARE_VERIFIED','EVIDENCE_COMMITTED','COMMITTED_VERIFIED','EVIDENCE_PUSHED','EVIDENCE_CI_VERIFIED','REPORT_RENDERED','COMPLETE']
SHA = __import__('re').compile(r'^[0-9a-f]{40}$')

def call(cmd, cwd, timeout=1900):
    p = subprocess.run(cmd, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode: raise RuntimeError((p.stderr or p.stdout).strip() or f'exit {p.returncode}')
    return p.stdout
def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent); os.close(fd)
    Path(tmp).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n', encoding='utf-8'); os.replace(tmp, path)
def load(path):
    value=json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(value,dict): raise RuntimeError(f'{path} must be an object')
    return value
def git_common(repo):
    p=Path(call(['git','rev-parse','--git-common-dir'],repo).strip()); return (repo/p).resolve() if not p.is_absolute() else p.resolve()
def fail(state, phase, message):
    state['error']={'phase':phase,'message':str(message)}; state['phase']=phase; write_json(Path(state['state_file']),state)
    print(json.dumps({'status':'blocked','phase':phase,'reason':'WORKFLOW_FAILED','diagnostic':str(message)[:500],'resume_command':f"python3 scripts/run-agent-evidence-workflow.py resume --repo {state['repo']}"},sort_keys=True)); raise SystemExit(5)
def validate_workflow(w):
    required={'schema_version','repository','branch','base_revision','version','evidence_root','evidence_slug','ci','evidence_commit_message'}
    if not isinstance(w,dict) or set(w)!=required or w.get('schema_version')!=1 or not isinstance(w.get('base_revision'),str) or not SHA.fullmatch(w['base_revision']): raise RuntimeError('invalid workflow input')
    ci=w['ci']; allowed={'policy','workflow','event','timeout_seconds','interval_seconds'}
    if not isinstance(ci,dict) or set(ci)!=allowed or ci['policy'] not in {'required','auto','optional','disabled'}: raise RuntimeError('invalid CI workflow input')
    if not isinstance(ci['timeout_seconds'],int) or ci['timeout_seconds']<=0 or not isinstance(ci['interval_seconds'],int) or ci['interval_seconds']<1: raise RuntimeError('invalid CI timing')
    if any(not isinstance(w[k],str) or not w[k] for k in ('repository','branch','version','evidence_root','evidence_slug','evidence_commit_message')): raise RuntimeError('invalid workflow identity')
    evidence_root=Path(w['evidence_root'])
    if evidence_root.is_absolute() or any(part in {'', '.', '..'} for part in evidence_root.parts): raise RuntimeError('invalid evidence root')
def quarantine_untracked(repo, evidence_root, destination):
    raw=subprocess.run(['git','-C',str(repo),'status','--porcelain=v1','-z','--untracked-files=all'],stdout=subprocess.PIPE,check=True).stdout
    tokens=raw.decode('utf-8').split('\0'); paths=[]; i=0
    while i < len(tokens) and tokens[i]:
        record=tokens[i]; i+=1
        if len(record)<3: raise RuntimeError('malformed git status record')
        status=record[:2]; path=record[3:]
        if status=='??': paths.append(path.rstrip('/'))
        elif status not in {'  '} or path: continue
        if status=='??' and i < len(tokens) and status[0] in 'RC': i+=1
    root=Path(evidence_root).as_posix().rstrip('/')+'/'
    candidates=set()
    for path in paths:
        if path.startswith(root): candidates.add(path.split('/')[len(root.split('/'))-1])
    for name in sorted(candidates):
        source=repo/evidence_root/name
        if not source.is_dir() or source.is_symlink(): raise RuntimeError('invalid untracked evidence candidate')
        tracked=subprocess.run(['git','-C',str(repo),'ls-files','--error-unmatch',str(source.relative_to(repo))],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode==0
        if tracked: raise RuntimeError('committed evidence cannot be quarantined')
        files=[]
        for item in source.iterdir():
            if item.is_symlink() or not item.is_file() or item.name not in {'manifest.json','evidence.json'}: raise RuntimeError('unsafe evidence candidate contents')
            files.append(item)
        target=destination/source.name; target.parent.mkdir(parents=True,exist_ok=True); hashes=[]
        for item in files: hashes.append({'source':str(item.relative_to(repo)),'sha256':hashlib.sha256(item.read_bytes()).hexdigest()})
        shutil.move(str(source),str(target)); q=destination/'quarantine.json'; prior=load(q) if q.exists() else {'items':[]}; prior.setdefault('items',[]).extend(hashes); write_json(q, prior)
def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest='command',required=True)
    runp=sub.add_parser('run'); runp.add_argument('--repo',required=True); runp.add_argument('--task',required=True)
    resp=sub.add_parser('resume'); resp.add_argument('--repo',required=True); resp.add_argument('--run-id')
    a=ap.parse_args(); repo=Path(a.repo).resolve(); common=git_common(repo); root=common/'gpt-review'; root.mkdir(parents=True,exist_ok=True)
    if a.command=='run':
        task=load_contract_json(Path(a.task)); required={'workflow','manifest_seed','evidence_plan','task_gate_contract'}
        if set(task)!=required: raise SystemExit('invalid task file')
        try:
            require_repository_evidence(repo)
        except ValueError as exc:
            raise SystemExit(f"ERROR: {exc}")
        (root/'runs').mkdir(parents=True,exist_ok=True)
        inputs=Path(tempfile.mkdtemp(prefix='evidence-inputs-',dir=root/'runs'))
        write_json(inputs/'workflow.json',task['workflow'])
        write_json(inputs/'manifest-seed.json',task['manifest_seed'])
        write_json(inputs/'evidence-plan.json',task['evidence_plan'])
        write_json(inputs/'task-gate-contract.json',task['task_gate_contract'])
        workflow=task['workflow']
        validate_workflow(workflow)
        try:
            validate_contract(load_contract_json(inputs/'task-gate-contract.json'))
        except TaskGateContractError as exc:
            raise SystemExit(f"TASK_GATE_CONTRACT_MISMATCH: {exc}")
        head=call(['git','rev-parse','HEAD'],repo).strip(); branch=call(['git','branch','--show-current'],repo).strip()
        run_id=hashlib.sha256((str(repo)+branch+head+(inputs/'workflow.json').read_bytes().hex()).encode()).hexdigest()[:20]
        state_dir=root/'runs'/run_id; state_dir.mkdir(parents=True,exist_ok=True)
        state={'repo':str(repo),'inputs':str(inputs),'run_id':run_id,'implementation_sha':head,'phase':'INITIALIZED','state_file':str(state_dir/'state.json'),'task_gate_contract':str(inputs/'task-gate-contract.json')}
        write_json(state_dir/'state.json',state); write_json(root/'active-evidence-run.json',{'run_id':run_id,'state_file':str(state_dir/'state.json')})
    else:
        try:
            require_repository_evidence(repo)
        except ValueError as exc:
            raise SystemExit(f"ERROR: {exc}")
        pointer=load(root/'active-evidence-run.json')
        if a.run_id and a.run_id != pointer.get('run_id'): raise SystemExit('run-id does not match active run')
        state=load(Path(pointer['state_file'])); state_dir=Path(state['state_file']).parent; inputs=Path(state['inputs']); workflow=load(inputs/'workflow.json'); validate_workflow(workflow)
        try:
            validate_contract(load_contract_json(Path(state['task_gate_contract'])))
        except (TaskGateContractError, KeyError) as exc:
            raise SystemExit(f"TASK_GATE_CONTRACT_MISMATCH: {exc}")
    phase=state.get('phase','INITIALIZED')
    def due(name):
        return PHASES.index(phase) < PHASES.index(name)
    def save(next_phase,**extra):
        state.update(extra); state['phase']=next_phase; write_json(Path(state['state_file']),state); print('EVIDENCE WORKFLOW: '+next_phase)
    try:
        if due('IDENTITY_VERIFIED'):
            if call(['git','branch','--show-current'],repo).strip()!=workflow['branch'] or Path(repo/'VERSION').read_text().strip()!=workflow['version']: raise RuntimeError('repository identity mismatch')
            if call(['git','remote','get-url','origin'],repo).strip()=='': raise RuntimeError('origin unavailable')
            save('IDENTITY_VERIFIED')
        if due('IMPLEMENTATION_CI_VERIFIED'):
            out=state_dir/'implementation-ci.json'
            if not out.exists():
                text=call(['python3',str(repo/'scripts/check-github-ci.py'),'--repository',workflow['repository'],'--sha',state['implementation_sha'],'--policy',workflow['ci']['policy'],'--workflow',workflow['ci']['workflow'],'--event',workflow['ci']['event'],'--wait','--timeout',str(workflow['ci']['timeout_seconds']),'--interval',str(workflow['ci']['interval_seconds']),'--format','json'],repo); out.write_text(text,encoding='utf-8')
            if load(out).get('state')!='success': raise RuntimeError('implementation CI was not successful')
            save('IMPLEMENTATION_CI_VERIFIED')
        if due('WORKTREE_CREATED'):
            evidence_root=Path(workflow['evidence_root']); quarantine_untracked(repo,evidence_root,Path(state['state_file']).parent/'quarantine')
            if call(['git','status','--porcelain','--untracked-files=all'],repo).strip(): raise RuntimeError('worktree must be clean after quarantine')
            wt=state_dir/'worktree'; call(['git','worktree','add','--detach',str(wt),state['implementation_sha']],repo); state['worktree']=str(wt); save('WORKTREE_CREATED')
        if due('TASK_GATE_CONTRACT_VERIFIED'):
            contract_path=Path(state['task_gate_contract']); generated_seed=state_dir/'manifest-seed.generated.json'; generated_plan=state_dir/'gate-plan.json'
            call(['python3',str(repo/'scripts/generate-task-gate-contract.py'),'generate','--contract',str(contract_path),'--manifest-seed',str(inputs/'manifest-seed.json'),'--manifest-output',str(generated_seed),'--gate-plan-output',str(generated_plan)],repo)
            state['manifest_seed']=str(generated_seed); state['gate_plan']=str(generated_plan); save('TASK_GATE_CONTRACT_VERIFIED',manifest_seed=str(generated_seed),gate_plan=str(generated_plan))
        if due('GATES_COMPLETED'):
            gateout=state_dir/'gate-run'; call(['python3',str(repo/'scripts/run-agent-gates.py'),'--repo',state['worktree'],'--plan',state['gate_plan'],'--task-gate-contract',state['task_gate_contract'],'--implementation-commit',state['implementation_sha'],'--output-dir',str(gateout)],repo); save('GATES_COMPLETED',gate_run=str(gateout/'gate-run.json'))
        if due('EVIDENCE_INPUTS_PREPARED'):
            seedout=state_dir/'manifest-seed.json'; planout=state_dir/'evidence-plan.json'; shutil.copy2(state['manifest_seed'],seedout); shutil.copy2(inputs/'evidence-plan.json',planout)
            evidence=Path(state.get('evidence','')) if state.get('evidence') else repo/workflow['evidence_root']/('patch-'+__import__('datetime').datetime.now(__import__('datetime').timezone.utc).strftime('%Y%m%d-%H%M%S')+'-'+workflow['evidence_slug']); state['evidence']=str(evidence); write_json(Path(state['state_file']),state)
            call(['python3',str(repo/'scripts/prepare-agent-evidence.py'),'--repo',str(repo),'--manifest-seed',str(seedout),'--evidence-plan',str(planout),'--base-revision',workflow['base_revision'],'--implementation-commit',state['implementation_sha'],'--evidence-directory',str(evidence.relative_to(repo)),'--manifest-output',str(evidence/'manifest.json'),'--resolved-plan-output',str(state_dir/'evidence-plan.resolved.json')],repo); save('EVIDENCE_INPUTS_PREPARED')
        if due('EVIDENCE_GENERATED'):
            call(['python3',str(repo/'scripts/generate-agent-evidence.py'),'--repo',str(repo),'--manifest',state['evidence']+'/manifest.json','--evidence-plan',str(state_dir/'evidence-plan.resolved.json'),'--gate-run',state['gate_run'],'--task-gate-contract',state['task_gate_contract'],'--implementation-commit',state['implementation_sha'],'--output',state['evidence']+'/evidence.json'],repo); save('EVIDENCE_GENERATED')
        if due('PREPARE_VERIFIED'):
            pack=state_dir/'pack'; pack.mkdir(exist_ok=True); shutil.copy2(state['evidence']+'/manifest.json',pack/'MANIFEST.json'); call(['python3',str(repo/'scripts/verify-agent-evidence.py'),'prepare','--pack',str(pack),'--repo',str(repo),'--implementation-commit',state['implementation_sha']],repo); save('PREPARE_VERIFIED')
        if due('EVIDENCE_COMMITTED'):
            rel=Path(state['evidence']).relative_to(repo); call(['git','add','--',str(rel/'manifest.json'),str(rel/'evidence.json')],repo); names=call(['git','diff','--cached','--name-only'],repo).splitlines(); expected={str(rel/'manifest.json'),str(rel/'evidence.json')}
            if set(names)!=expected: raise RuntimeError('evidence commit scope is not exactly two files')
            existing=call(['git','log','-1','--format=%H','--all','--',str(rel/'manifest.json'),str(rel/'evidence.json')],repo).strip()
            if existing and set(call(['git','diff-tree','--no-commit-id','--name-only','-r',existing],repo).splitlines())==expected: state['evidence_commit']=existing
            else: call(['git','commit','-m',workflow['evidence_commit_message']],repo); state['evidence_commit']=call(['git','rev-parse','HEAD'],repo).strip()
            save('EVIDENCE_COMMITTED')
        if due('COMMITTED_VERIFIED'):
            call(['python3',str(repo/'scripts/verify-agent-evidence.py'),'committed','--pack',str(state_dir/'pack'),'--repo',str(repo),'--implementation-commit',state['implementation_sha'],'--evidence-commit',state['evidence_commit']],repo); save('COMMITTED_VERIFIED')
        if due('EVIDENCE_PUSHED'):
            remote=call(['git','ls-remote','origin',f"refs/heads/{workflow['branch']}"],repo).strip().split()[0]
            if remote and call(['git','merge-base','--is-ancestor',remote,state['evidence_commit']],repo,timeout=60) is None: pass
            call(['git','push','origin',f"refs/heads/{workflow['branch']}:refs/heads/{workflow['branch']}"],repo); save('EVIDENCE_PUSHED')
        if due('EVIDENCE_CI_VERIFIED'):
            out=state_dir/'evidence-ci.json'
            if out.exists() and load(out).get('state')=='success': text=out.read_text(encoding='utf-8')
            else: text=call(['python3',str(repo/'scripts/check-github-ci.py'),'--repository',workflow['repository'],'--sha',state['evidence_commit'],'--policy',workflow['ci']['policy'],'--workflow',workflow['ci']['workflow'],'--event',workflow['ci']['event'],'--wait','--timeout',str(workflow['ci']['timeout_seconds']),'--interval',str(workflow['ci']['interval_seconds']),'--format','json'],repo); out.write_text(text,encoding='utf-8')
            if load(out).get('state')!='success': raise RuntimeError('evidence CI was not successful')
            save('EVIDENCE_CI_VERIFIED')
        if due('REPORT_RENDERED'):
            report=state_dir/'agent-report.txt'; report.write_text(call(['python3',str(repo/'scripts/render-agent-report.py'),'--evidence',state['evidence']+'/evidence.json','--ci-result','implementation-ci='+str(state_dir/'implementation-ci.json'),'--ci-result','evidence-ci='+str(state_dir/'evidence-ci.json')],repo),encoding='utf-8'); state['report']=str(report); save('REPORT_RENDERED')
        if due('COMPLETE'):
            if state.get('worktree') and Path(state['worktree']).exists(): call(['git','worktree','remove','--force',state['worktree']],repo)
            save('COMPLETE')
        print('EVIDENCE WORKFLOW: COMPLETE')
    except Exception as exc: fail(state,state.get('phase','INITIALIZED'),exc)
if __name__=='__main__': main()
