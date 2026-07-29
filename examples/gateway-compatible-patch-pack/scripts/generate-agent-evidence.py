#!/usr/bin/env python3
"""Generate committed evidence from a manifest, evidence plan, gate run, and CI JSON."""
import argparse, hashlib, json, os, subprocess, tempfile
from pathlib import Path

def die(msg): print(f"ERROR: {msg}", file=__import__('sys').stderr); raise SystemExit(5)
def read_json(p):
    try: return json.loads(Path(p).read_text(encoding='utf-8'))
    except Exception as e: die(f"invalid JSON {p}: {e}")
def proof(repo, commit, item):
    path=item['path']; a,b=item['lines']
    raw=__import__('subprocess').check_output(['git','-C',str(repo),'show',f'{commit}:{path}'])
    lines=raw.decode('utf-8').splitlines(True)
    if a<1 or b<a or b>len(lines): die(f"invalid proof range: {path}")
    selected=''.join(lines[a-1:b]).encode()
    if item.get('symbol') and item['symbol'] not in selected.decode('utf-8'): die(f"symbol outside proof range: {path}")
    return dict(item, sha256=hashlib.sha256(selected).hexdigest())

def validate_worktree(repo, manifest_path, output_path, evidence_directory):
    repo = repo.resolve(); manifest_path = manifest_path.resolve(); output_path = output_path.resolve()
    evidence_directory = evidence_directory.resolve()
    expected_manifest = evidence_directory / 'manifest.json'
    expected_output = evidence_directory / 'evidence.json'
    for label, path in (('manifest', manifest_path), ('output', output_path), ('evidence directory', evidence_directory)):
        if path != repo and repo not in path.parents: die(f'{label} is outside repository')
    if manifest_path != expected_manifest: die('supplied manifest path does not match manifest.evidence_directory')
    if output_path != expected_output: die('supplied output path does not match manifest.evidence_directory')
    if evidence_directory.is_symlink(): die('evidence directory must not be a symlink')
    if output_path.exists(): die('output already exists')
    if not evidence_directory.is_dir(): die('evidence directory is missing')
    for child in evidence_directory.iterdir():
        if child.is_symlink() or not child.is_file() or child.name not in {'manifest.json', 'evidence.json'}:
            die('evidence directory contains an invalid file or nested directory')
    raw = subprocess.check_output(['git','-C',str(repo),'status','--porcelain=v1','-z','--untracked-files=all'])
    records = raw.decode('utf-8', errors='surrogateescape').split('\0')
    allowed = {expected_manifest.relative_to(repo).as_posix(), expected_output.relative_to(repo).as_posix()}
    for record in records:
        if not record: continue
        status, rel = record[:2], record[3:]
        rel = Path(rel).as_posix()
        if status == '??' and rel.endswith('/'):
            directory = (repo / rel.rstrip('/')).resolve()
            if directory != evidence_directory: die('untracked directory is outside declared evidence directory')
            continue
        if status not in {'??', 'A '} or rel not in allowed:
            die('repository contains unrelated, modified, deleted, renamed, copied, or type-changed paths')
    if not manifest_path.is_file(): die('manifest file is missing')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--evidence-plan',required=True); ap.add_argument('--gate-run',required=True); ap.add_argument('--implementation-commit',required=True); ap.add_argument('--output',required=True); ap.add_argument('--ci-result',action='append',default=[]); a=ap.parse_args()
    repo=Path(a.repo).resolve(); sha=a.implementation_commit
    if len(sha)!=40 or any(c not in '0123456789abcdef' for c in sha): die('invalid implementation SHA')
    if subprocess.run(['git','-C',str(repo),'cat-file','-e',sha+'^{commit}']).returncode: die('implementation commit missing')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=sha: die('HEAD mismatch')
    output=Path(a.output).resolve(); manifest=read_json(a.manifest); plan=read_json(a.evidence_plan); run=read_json(a.gate_run)
    evidence_directory=(repo / manifest.get('evidence_directory','')).resolve()
    validate_worktree(repo, Path(a.manifest), output, evidence_directory)
    if run.get('implementation_commit') != sha or run.get('status') != 'pass': die('gate-run identity or status mismatch')
    manifest_ids={g['id'] for g in manifest.get('gates',[]) if g.get('kind','command') == 'command'}
    run_ids=[g.get('id') for g in run.get('gates',[])]
    if len(run_ids)!=len(set(run_ids)) or set(run_ids)!=manifest_ids: die('gate-run gate IDs do not match manifest')
    mids={r['id'] for r in manifest.get('requirements',[])}; req=[]; seen_req=set()
    for item in plan.get('requirements',[]):
        if item['id'] not in mids: die(f"requirement mismatch: {item['id']}")
        if item['id'] in seen_req: die(f"duplicate requirement: {item['id']}")
        seen_req.add(item['id'])
        record={'id':item['id'],'status':item['status'],'proofs':[proof(repo,sha,p) for p in item['proofs']]}
        for key in ('note','deviation'):
            if key in item: record[key]=item[key]
        req.append(record)
    if seen_req != mids: die('evidence-plan requirements incomplete')
    ci={}
    seen_ci=set()
    for pair in a.ci_result:
        if '=' not in pair: die('invalid ci-result')
        key,path=pair.split('=',1)
        if key in seen_ci: die('duplicate ci-result key')
        seen_ci.add(key); ci[key]=read_json(path)
        value=ci[key]
        target_repo=manifest.get('target',{}).get('repository')
        if value.get('repository')!=target_repo or value.get('sha')!=sha or value.get('checked_sha')!=sha or value.get('state')!='success' or value.get('status')!='completed' or value.get('conclusion')!='success' or value.get('blocking') is not False: die('CI identity or success mismatch')
        if not isinstance(value.get('run_id'),int) or value['run_id']<=0 or (value.get('job_id') is not None and (not isinstance(value['job_id'],int) or value['job_id']<=0)): die('invalid CI IDs')
        if not str(value.get('run_url','')).startswith('https://github.com/'): die('invalid CI run URL')
        if value.get('job_id') is not None and not str(value.get('job_url','')).startswith('https://github.com/'): die('invalid CI job URL')
    gates=[]
    for g in run.get('gates',[]):
        item={k:g[k] for k in ('id','status','exit') if k in g}
        if g.get('metrics'): item['metrics']=g['metrics']; item['summary']='All required gates passed; '+', '.join(f'{k}={v}' for k,v in sorted(g['metrics'].items()))+'.'
        elif 'tests' in g: item['tests']=g['tests']; item['summary']=g.get('summary','')
        else: item['summary']=g.get('summary','')
        gates.append(item)
    ci_gate_ids={g['id'] for g in manifest.get('gates',[]) if g.get('kind') == 'github-actions'}
    if set(ci) != ci_gate_ids: die('CI result keys do not match manifest CI gates')
    for key,value in ci.items(): gates.append({'id':key,'status':'pass','run':value.get('run_id'),'job':value.get('job_id'),'url':value.get('run_url'),'run_url':value.get('run_url'),'job_url':value.get('job_url'),'summary':value.get('message','')})
    result={'schema_version':1,'implementation_commit':sha,'requirements':req,'gates':gates,'deviations':plan.get('deviations',[])}
    target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=target.parent); os.close(fd); Path(tmp).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,target)
    print(f"Evidence generated: {target}")
if __name__=='__main__': main()
