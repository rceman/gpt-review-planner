import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]


class GateEvidenceAutomationTests(unittest.TestCase):
    def test_schemas_and_portable_scripts(self):
        for path in ("schemas/gate-plan.schema.json", "schemas/gate-run.schema.json", "schemas/evidence-plan.schema.json"):
            json.loads((ROOT / path).read_text())
        for name in ("run-agent-gates.py", "generate-agent-evidence.py", "render-agent-report.py"):
            self.assertEqual((ROOT / "scripts" / name).read_bytes(), (ROOT / "templates/executable-patch-pack/scripts" / name).read_bytes())

    def test_runner_binds_exact_head_and_extracts_counts(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            (repo / "x").write_text("x")
            subprocess.run(["git", "-C", str(repo), "add", "x"], check=True)
            subprocess.run(["git", "-C", str(repo), "-c", "user.email=a@b", "-c", "user.name=a", "commit", "-qm", "x"], check=True)
            sha = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            plan = Path(td) / "gate.json"
            plan.write_text(json.dumps({"schema_version":1,"gates":[{"id":"local","steps":[{"id":"u","argv":["python3","-c","print('Ran 2 tests in 0.01s')"],"parser":"unittest","timeout_seconds":5,"metric":"unittest"}]}]}))
            out = Path(td) / "out"
            subprocess.run(["python3", str(ROOT / "scripts/run-agent-gates.py"), "--repo", str(repo), "--plan", str(plan), "--implementation-commit", sha, "--output-dir", str(out)], check=True)
            result = json.loads((out / "gate-run.json").read_text())
            self.assertEqual(result["implementation_commit"], sha)
            self.assertEqual(result["gates"][0]["metrics"]["unittest"], 2)

    def test_renderer_is_compact(self):
        with tempfile.TemporaryDirectory() as td:
            evidence = Path(td) / "e.json"
            evidence.write_text(json.dumps({"gates":[{"id":"local-gates","metrics":{"pytest":150,"unittest":148}}]}))
            result = subprocess.check_output(["python3", str(ROOT / "scripts/render-agent-report.py"), "--evidence", str(evidence)], text=True)
            self.assertEqual(result.strip(), "Local gates: success | pytest=150 | unittest=148")


if __name__ == "__main__":
    unittest.main()
