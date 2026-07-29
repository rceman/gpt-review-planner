import json, subprocess, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]
HELPER=ROOT/'scripts/prepare-agent-evidence.py'

class PrepareAgentEvidenceTests(unittest.TestCase):
    def git(self, repo, *args):
        return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
    def test_behavioral_scope_and_selectors(self):
        with tempfile.TemporaryDirectory() as td:
            repo=Path(td)/'repo'; repo.mkdir(); self.git(repo,'init','-q'); subprocess.run(['git','-C',str(repo),'switch','-c','main'],check=True,stdout=subprocess.DEVNULL)
            (repo/'old.txt').write_text('old\n'); (repo/'same.txt').write_text('same\n'); self.git(repo,'add','.'); subprocess.run(['git','-C',str(repo),'-c','user.email=a@b','-c','user.name=a','commit','-qm','base'],check=True)
            base=self.git(repo,'rev-parse','HEAD'); (repo/'old.txt').rename(repo/'renamed.txt'); (repo/'same.txt').write_text('changed\n'); (repo/'new.txt').write_text('new\n'); self.git(repo,'add','-A'); subprocess.run(['git','-C',str(repo),'-c','user.email=a@b','-c','user.name=a','commit','-qm','change'],check=True); sha=self.git(repo,'rev-parse','HEAD')
            (repo/'copy.txt').write_text('new\n'); subprocess.run(['git','-C',str(repo),'add','copy.txt'],check=True); subprocess.run(['git','-C',str(repo),'-c','user.email=a@b','-c','user.name=a','commit','-qm','copy'],check=True); sha=self.git(repo,'rev-parse','HEAD')
            seed=Path(td)/'seed.json'; seed.write_text(json.dumps({'schema_version':2,'title':'x','description':'x','baseline_release':'v1.3.0','workflow':{'repository':'planner','version':'1.3.0','commit':'implementation','document':'GPT_REVIEW_PLANNER.md'},'target':{'repository':'owner/repo','branch':'main','base_revision':'stale'},'requirements':[{'id':'R','summary':'r','acceptance':['a']}],'gates':[{'id':'local-gates','name':'g','kind':'command','command':'x'}]}))
            plan=Path(td)/'plan.json'; plan.write_text(json.dumps({'schema_version':1,'requirements':[{'id':'R','status':'pass','proofs':[{'kind':'source','path':'new.txt','selector':{'contains':'new'}}]}],'deviations':[]}))
            ev='.gpt-review/evidence/v1.3.0/patch-20260729-120000-evidence-automation'; out=Path(td)/'resolved.json'; manifest=repo/ev/'manifest.json'
            subprocess.run(['python3',str(HELPER),'--repo',str(repo),'--manifest-seed',str(seed),'--evidence-plan',str(plan),'--base-revision',base,'--implementation-commit',sha,'--evidence-directory',ev,'--manifest-output',str(manifest),'--resolved-plan-output',str(out)],check=True)
            self.assertTrue(manifest.is_file()); self.assertTrue(out.is_file()); self.assertEqual(json.loads(out.read_text())['requirements'][0]['proofs'][0]['lines'],[1,1])
            self.assertEqual(json.loads(manifest.read_text())['target']['base_revision'],base)
    def test_portable_copies_match(self):
        data=HELPER.read_bytes(); self.assertEqual(data,(ROOT/'templates/executable-patch-pack/scripts/prepare-agent-evidence.py').read_bytes()); self.assertEqual(data,(ROOT/'examples/gateway-compatible-patch-pack/scripts/prepare-agent-evidence.py').read_bytes())
if __name__=='__main__': unittest.main()
