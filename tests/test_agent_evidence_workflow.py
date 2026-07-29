import unittest
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
if __name__=='__main__': unittest.main()
