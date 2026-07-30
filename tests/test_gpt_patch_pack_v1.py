from __future__ import annotations
import importlib.util,json,tarfile,tempfile,io,sys
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("runner",ROOT/"scripts/gpt-patch-pack-runner-v1.py")
runner=importlib.util.module_from_spec(SPEC); SPEC.loader.exec_module(runner)
class TestV1(unittest.TestCase):
 def archive(self, members):
  raw=io.BytesIO()
  with tarfile.open(fileobj=raw, mode="w:gz") as tf:
   for name, data in members:
    info=tarfile.TarInfo(name); info.size=len(data); info.mode=0o644; tf.addfile(info,io.BytesIO(data))
  return raw.getvalue()

 def test_data_only_archive_rejects_extra_member(self):
  data=self.archive([("p/MANIFEST.json",b"{}"),("p/SHA256SUMS",b""),("p/AGENT_TASK.md",b"task"),("p/payload/changes.patch",b"patch"),("p/payload/apply.py",b"raise SystemExit(99)")])
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"x.tar.gz"; path.write_bytes(data)
   with self.assertRaises(runner.PackError): runner.safe_extract(path,Path(d)/"out")

 def test_data_only_archive_rejects_missing_canonical_member(self):
  data=self.archive([("p/MANIFEST.json",b"{}"),("p/SHA256SUMS",b""),("p/AGENT_TASK.md",b"task")])
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"x.tar.gz"; path.write_bytes(data)
   with self.assertRaises(runner.PackError): runner.safe_extract(path,Path(d)/"out")

 def test_data_only_archive_rejects_symlink_member(self):
  raw=io.BytesIO()
  with tarfile.open(fileobj=raw,mode="w:gz") as tf:
   info=tarfile.TarInfo("p/link"); info.type=tarfile.SYMTYPE; info.linkname="/etc/passwd"; tf.addfile(info)
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"x.tar.gz"; path.write_bytes(raw.getvalue())
   with self.assertRaises(runner.PackError): runner.safe_extract(path,Path(d)/"out")

 def test_data_only_archive_rejects_traversal_member(self):
  data=self.archive([("../escape",b"x")])
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"x.tar.gz"; path.write_bytes(data)
   with self.assertRaises(runner.PackError): runner.safe_extract(path,Path(d)/"out")

 def test_data_only_archive_rejects_casefold_collision(self):
  data=self.archive([("p/AGENT_TASK.md",b"x"),("p/agent_task.md",b"y")])
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/"x.tar.gz"; path.write_bytes(data)
   with self.assertRaises(runner.PackError): runner.safe_extract(path,Path(d)/"out")

 def test_gate_output_limit_is_streaming_and_bounded(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(runner.PackError, "output exceeded"):
    runner.run([sys.executable, "-c", "print('x'*1000000)"], Path(d), output_limit=1024)

 def test_gate_timeout_terminates_process_group(self):
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(runner.PackError, "timed out"):
    runner.run([sys.executable, "-c", "import time; time.sleep(5)"], Path(d), timeout=1)
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
