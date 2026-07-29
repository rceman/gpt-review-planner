#!/usr/bin/env python3
import argparse,json
def main():
 p=argparse.ArgumentParser(); p.add_argument('--evidence',required=True); p.add_argument('--ci-result',action='append',default=[]); a=p.parse_args(); e=json.load(open(a.evidence));
 for g in e.get('gates',[]):
  if g.get('metrics'):
   print('Local gates: success | '+' | '.join(f'{k}={v}' for k,v in sorted(g['metrics'].items())))
  elif g.get('run') is not None:
   print(f"{g['id']}: success | run={g['run']} | job={g.get('job')} | url={g.get('url')}")
if __name__=='__main__': main()
