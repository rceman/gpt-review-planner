import unittest
from pathlib import Path

ROOT=Path(__file__).parents[1]
class PrepareAgentEvidenceTests(unittest.TestCase):
    def test_helper_has_required_bindings_and_selectors(self):
        text=(ROOT/'scripts/prepare-agent-evidence.py').read_text()
        for value in ('merge-base','--name-status','selector','contains','start','end','evidence directory identity','workflow', 'files_created'):
            self.assertIn(value,text)
    def test_portable_copies_match(self):
        for name in ('prepare-agent-evidence.py',):
            root=(ROOT/'scripts'/name).read_bytes()
            self.assertEqual(root,(ROOT/'templates/executable-patch-pack/scripts'/name).read_bytes())
            self.assertEqual(root,(ROOT/'examples/gateway-compatible-patch-pack/scripts'/name).read_bytes())
if __name__=='__main__': unittest.main()
