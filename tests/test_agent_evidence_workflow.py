import json, subprocess, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).parents[1]
class WorkflowContractTests(unittest.TestCase):
    def test_runner_and_schema_exist(self):
        self.assertTrue((ROOT/'scripts/run-agent-evidence-workflow.py').exists())
        self.assertTrue((ROOT/'schemas/agent-evidence-workflow.schema.json').exists())
    def test_portable_runner_copies_match(self):
        data=(ROOT/'scripts/run-agent-evidence-workflow.py').read_bytes()
        self.assertEqual(data,(ROOT/'templates/executable-patch-pack/scripts/run-agent-evidence-workflow.py').read_bytes())
        self.assertEqual(data,(ROOT/'examples/gateway-compatible-patch-pack/scripts/run-agent-evidence-workflow.py').read_bytes())
    def test_safe_untracked_evidence_is_quarantined(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('runner',ROOT/'scripts/run-agent-evidence-workflow.py'); mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp); subprocess.run(['git','init','-q'],cwd=repo,check=True); subprocess.run(['git','config','user.email','t@example.invalid'],cwd=repo,check=True); subprocess.run(['git','config','user.name','Test'],cwd=repo,check=True)
            (repo/'x').write_text('x'); subprocess.run(['git','add','x'],cwd=repo,check=True); subprocess.run(['git','commit','-qm','init'],cwd=repo,check=True)
            ev=repo/'.gpt-review/evidence/v1.3.0/patch-20990101-010101-evidence-automation'; ev.mkdir(parents=True); (ev/'manifest.json').write_text('{}')
            dest=repo/'.git/gpt-review/runs/test/quarantine'; mod.quarantine_untracked(repo,Path('.gpt-review/evidence/v1.3.0'),dest)
            self.assertFalse(ev.exists()); self.assertTrue((dest/ev.name/'manifest.json').exists()); self.assertTrue((dest/'quarantine.json').exists())
    def test_task_shape_is_single_specification(self):
        text=(ROOT/'scripts/run-agent-evidence-workflow.py').read_text()
        self.assertIn("--task", text); self.assertIn("active-evidence-run.json", text)
if __name__=='__main__': unittest.main()
