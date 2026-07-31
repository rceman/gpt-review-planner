#!/usr/bin/env python3
"""Prepare a generated manifest and resolved evidence plan from semantic inputs."""
import argparse, json, os, re, subprocess, tempfile
from datetime import datetime, timezone
from pathlib import Path

SHA_RE=re.compile(r'^[0-9a-f]{40}$')
PATCH_RE=re.compile(r'^patch-(\d{8})-(\d{6})-(evidence-automation)(?:-(\d{2}))?$')
PROOF_KINDS={'source','test','workflow','documentation','json','deletion'}

def die(msg): print('ERROR: '+msg, file=__import__('sys').stderr); raise SystemExit(5)
def load(path):
    try: return json.loads(Path(path).read_text(encoding='utf-8'))
    except Exception as e: die(f'invalid JSON: {e}')
def atomic(path, value):
    path.parent.mkdir(parents=True,exist_ok=True); fd,tmp=tempfile.mkstemp(dir=path.parent); os.close(fd)
    Path(tmp).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.replace(tmp,path)
def safe_rel(value):
    p=Path(value)
    if p.is_absolute() or '..' in p.parts or not value or '\\' in value: die('invalid repository-relative path')
    return p.as_posix()
def unique_line(lines, anchor, label):
    hits=[i+1 for i,line in enumerate(lines) if anchor in line]
    if len(hits)!=1: die(f'{label} anchor occurrence count is {len(hits)}')
    return hits[0]
def resolve_proof(repo, commit, item):
    if item.get('kind') not in PROOF_KINDS: die('unsupported proof kind')
    allowed={'kind','path','lines','selector','symbol','pointer','value'}
    if set(item)-allowed: die('unknown proof field')
    path=safe_rel(item.get('path',''))
    raw=subprocess.check_output(['git','-C',str(repo),'show',f'{commit}:{path}'])
    text=raw.decode('utf-8'); lines=text.splitlines()
    has_lines='lines' in item; selector=item.get('selector')
    if has_lines == (selector is not None): die('proof must contain exactly one of lines or selector')
    if has_lines:
        bounds=item['lines']
        if not isinstance(bounds,list) or len(bounds)!=2 or not all(isinstance(x,int) and x>=1 for x in bounds): die('invalid proof lines')
        start,end=bounds
    else:
        if not isinstance(selector,dict) or set(selector)-{'contains','start','end'}: die('invalid selector')
        if 'contains' in selector:
            if set(selector)!= {'contains'} or not selector['contains']: die('invalid contains selector')
            start=end=unique_line(lines,selector['contains'],'contains')
        else:
            if set(selector)!= {'start','end'} or not selector['start'] or not selector['end']: die('invalid range selector')
            start=unique_line(lines,selector['start'],'start'); end=unique_line(lines,selector['end'],'end')
    if end<start or end>len(lines) or end-start+1>160: die('invalid or overlong proof range')
    if item.get('symbol') and item['symbol'] not in '\n'.join(lines[start-1:end]): die('symbol outside resolved range')
    result={k:item[k] for k in item if k!='selector' and k!='lines'}; result['lines']=[start,end]
    return result
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--repo',required=True); ap.add_argument('--manifest-seed',required=True); ap.add_argument('--evidence-plan',required=True); ap.add_argument('--base-revision',required=True); ap.add_argument('--implementation-commit',required=True); ap.add_argument('--evidence-directory',required=True); ap.add_argument('--manifest-output',required=True); ap.add_argument('--resolved-plan-output',required=True); a=ap.parse_args()
    repo=Path(a.repo).resolve(); seed=load(a.manifest_seed); plan=load(a.evidence_plan); sha=a.implementation_commit
    if not repo.is_dir() or not SHA_RE.fullmatch(sha) or not SHA_RE.fullmatch(a.base_revision): die('invalid repository or SHA')
    if subprocess.run(['git','-C',str(repo),'cat-file','-e',sha+'^{commit}']).returncode or subprocess.run(['git','-C',str(repo),'cat-file','-e',a.base_revision+'^{commit}']).returncode: die('commit does not exist')
    if subprocess.run(['git','-C',str(repo),'merge-base','--is-ancestor',a.base_revision,sha]).returncode: die('base is not an ancestor')
    if subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()!=sha: die('HEAD mismatch')
    if subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True): die('worktree must be clean')
    target=seed.get('target',{}); branch=subprocess.check_output(['git','-C',str(repo),'branch','--show-current'],text=True).strip()
    if branch!=target.get('branch') or not target.get('repository'): die('repository identity mismatch')
    ev=safe_rel(a.evidence_directory); evpath=(repo/ev).resolve(); out=Path(a.manifest_output).resolve(); resolved=Path(a.resolved_plan_output).resolve()
    common_raw=subprocess.check_output(['git','-C',str(repo),'rev-parse','--git-common-dir'],text=True).strip()
    common=(repo/Path(common_raw)).resolve() if not Path(common_raw).is_absolute() else Path(common_raw).resolve()
    if repo not in evpath.parents or not evpath.name.startswith('patch-') or not PATCH_RE.fullmatch(evpath.name): die('invalid evidence directory identity')
    resolved_in_worktree=(resolved==repo or repo in resolved.parents)
    resolved_in_common=(resolved==common or common in resolved.parents)
    if out != evpath/'manifest.json' or (resolved_in_worktree and not resolved_in_common): die('invalid output binding')
    if out.exists() or resolved.exists() or evpath.exists(): die('output or evidence directory already exists')
    statuses=subprocess.check_output(['git','-C',str(repo),'diff','--name-status','-z','-M','-C','--find-copies-harder',a.base_revision+'..'+sha,'--'])
    created=[]; modified=[]; deleted=[]; tokens=statuses.decode('utf-8').split('\0'); i=0
    while i < len(tokens) and tokens[i]:
        code=tokens[i]; i+=1; kind=code[0]
        if kind in 'RC':
            if i+1 >= len(tokens) or not tokens[i] or not tokens[i+1]: die('truncated rename/copy record')
            old,new=safe_rel(tokens[i]),safe_rel(tokens[i+1]); i+=2
            if kind=='R': deleted.append(old)
            created.append(new)
        elif kind in 'AMDT':
            if i >= len(tokens) or not tokens[i]: die('truncated status record')
            p=safe_rel(tokens[i]); i+=1
            (created if kind=='A' else deleted if kind=='D' else modified).append(p)
        else: die('unsupported diff status')
    evprefix=ev.rstrip('/')+'/'
    created=[p for p in created if not p.startswith(evprefix)]; modified=[p for p in modified if not p.startswith(evprefix)]; deleted=[p for p in deleted if not p.startswith(evprefix)]
    if len(set(created+modified+deleted))!=len(created+modified+deleted): die('duplicate scope path')
    match=PATCH_RE.fullmatch(evpath.name)
    try: stamp=datetime.strptime(match.group(1)+match.group(2), '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    except (ValueError, AttributeError): die('invalid evidence directory calendar timestamp')
    manifest=dict(seed); manifest.update({'schema_version':2,'patch_id':evpath.name,'patch_timestamp':match.group(1)+'-'+match.group(2),'patch_slug':match.group(3),'created_at':stamp.strftime('%Y-%m-%dT%H:%M:%SZ'),'evidence_directory':ev,'files_created':sorted(created),'files_modified':sorted(modified),'files_deleted':sorted(deleted)})
    manifest.setdefault('target',{})['base_revision']=a.base_revision
    workflow=manifest.setdefault('workflow',{}); commit_value=workflow.get('commit')
    if commit_value in {'HEAD','implementation'}: workflow['commit']=sha
    elif commit_value != sha: die('workflow.commit must be implementation, HEAD, or the exact implementation SHA')
    resolved_plan={'schema_version':1,'requirements':[],'deviations':plan.get('deviations',[])}
    for req in plan.get('requirements',[]):
        item={k:req[k] for k in req if k in {'id','status','note','deviation'}}; item['proofs']=[resolve_proof(repo,sha,p) for p in req.get('proofs',[])]; resolved_plan['requirements'].append(item)
    atomic(resolved,resolved_plan)
    try: atomic(out,manifest)
    except Exception:
        if resolved.exists(): resolved.unlink()
        raise
    print(f'Evidence inputs prepared: manifest={out} resolved_plan={resolved}')
if __name__=='__main__': main()
