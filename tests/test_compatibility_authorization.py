from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class TestCompatibilityPolicy(unittest.TestCase):
 def test_policy(self):
  text=(ROOT/"docs/COMPATIBILITY_AUTHORIZATION.md").read_text()
  self.assertIn("BLOCKED_UNAUTHORIZED_COMPATIBILITY_CHANGE",text)
  self.assertIn("Compatibility authorization: not granted",text)
 def test_no_old_templates(self):
  self.assertFalse((ROOT/"templates/executable-patch-pack").exists())
  self.assertFalse((ROOT/"examples/gateway-compatible-patch-pack").exists())
if __name__=="__main__": unittest.main()
