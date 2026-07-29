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
    mids={r['id'] for r in manifest.get('requirements',[])}; req=[]
    for item in plan.get('requirements',[]):
        if item['id'] not in mids: die(f"requirement mismatch: {item['id']}")
        req.append({**item,'proofs':[proof(repo,sha,p) for p in item['proofs']]})
    ci={}
    for pair in a.ci_result:
        if '=' not in pair: die('invalid ci-result')
        key,path=pair.split('=',1); ci[key]=read_json(path)
        value=ci[key]
        if value.get('repository')!=manifest['workflow']['repository'] or value.get('sha')!=sha or value.get('checked_sha')!=sha or value.get('state')!='success' or value.get('conclusion')!='success': die('CI identity or success mismatch')
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
