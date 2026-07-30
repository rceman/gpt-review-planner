from __future__ import annotations
import importlib.util,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("runner",ROOT/"scripts/gpt-patch-pack-runner-v1.py")
runner=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)
class TestV1(unittest.TestCase):
 def test_unsafe_paths(self):
  for value in ("","/a","../a","a/../b","a\\b","a\nb"):
   with self.assertRaises(runner.PackError): runner.normalize_relative(value,"test")
 def test_single_format(self):
  schema=json.loads((ROOT/"schemas/patch-manifest.schema.json").read_text())
  self.assertEqual(schema["properties"]["format"]["const"],"gpt-patch-pack-v1")
 def test_evidence_compatibility_fields(self):
  schema=json.loads((ROOT/"schemas/agent-evidence.schema.json").read_text())
  for field in ("compatibility_scope","compatibility_authorized","compatibility_features_added","legacy_paths_added","fallbacks_added","migration_behavior_added"):
   self.assertIn(field,schema["required"])
if __name__=="__main__": unittest.main()
