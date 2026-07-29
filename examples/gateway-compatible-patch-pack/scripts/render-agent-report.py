#!/usr/bin/env python3
import argparse, json, re

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--evidence',required=True); ap.add_argument('--ci-result',action='append',default=[]); a=ap.parse_args()
    evidence=json.load(open(a.evidence,encoding='utf-8'))
    for gate in evidence.get('gates',[]):
        if gate.get('metrics'):
            print('Local gates: success | '+' | '.join(f'{k}={gate["metrics"][k]}' for k in sorted(gate['metrics'])))
    for spec in a.ci_result:
        if '=' not in spec: raise SystemExit('invalid --ci-result')
        label,path=spec.split('=',1); data=json.load(open(path,encoding='utf-8'))
        if data.get('state') != 'success' or data.get('conclusion') != 'success' or data.get('blocking') is not False:
            print(f'{label}: failed | blocking=true | sha={data.get("sha")} | run={data.get("run_id")} | job={data.get("job_id")} | exit=3 | message={data.get("message")}')
            continue
        print(f'{label}: success | sha={data["sha"]} | run={data["run_id"]} | job={data.get("job_id")} | run_url={data["run_url"]} | job_url={data.get("job_url")}')
if __name__=='__main__': main()
