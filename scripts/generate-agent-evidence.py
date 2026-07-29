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
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--manifest',required=True); ap.add_argument('--evidence-plan',required=True); ap.add_argument('--gate-run',required=True); ap.add_argument('--implementation-commit',required=True); ap.add_argument('--output',required=True); ap.add_argument('--ci-result',action='append',default=[]); a=ap.parse_args()
    repo=Path(a.repo).resolve(); sha=a.implementation_commit
    if len(sha)!=40 or any(c not in '0123456789abcdef' for c in sha): die('invalid implementation SHA')
    if subprocess.run(['git','-C',str(repo),'cat-file','-e',sha+'^{commit}']).returncode: die('implementation commit missing')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=sha: die('HEAD mismatch')
    dirty=subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True)
    output=Path(a.output).resolve(); allowed={str(output),str(output.parent/'manifest.json')}
    if any(line[3:].strip() not in allowed for line in dirty.splitlines()): die('repository is dirty except intended evidence files')
    manifest=read_json(a.manifest); plan=read_json(a.evidence_plan); run=read_json(a.gate_run)
    if run.get('implementation_commit') != sha or run.get('status') != 'pass': die('gate-run identity or status mismatch')
    manifest_ids={g['id'] for g in manifest.get('gates',[])}
    run_ids=[g.get('id') for g in run.get('gates',[])]
    if len(run_ids)!=len(set(run_ids)) or set(run_ids)!=manifest_ids: die('gate-run gate IDs do not match manifest')
    evidence_dir=(repo/manifest.get('evidence_directory','')).resolve()
    output=Path(a.output).resolve()
    if output.exists(): die('output already exists')
    if output.parent != evidence_dir: die('output is outside manifest evidence directory')
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
    for key,value in ci.items(): gates.append({'id':key,'status':'pass','run':value.get('run_id'),'job':value.get('job_id'),'url':value.get('job_url') or value.get('run_url'),'summary':value.get('message','')})
    result={'schema_version':1,'implementation_commit':sha,'requirements':req,'gates':gates,'deviations':plan.get('deviations',[])}
    target=Path(a.output); target.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=target.parent); os.close(fd); Path(tmp).write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,target)
    print(f"Evidence generated: {target}")
if __name__=='__main__': main()
