from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("v1runner", ROOT / "scripts/gpt-patch-pack-runner-v1.py")
runner = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(runner)


class PatchPackSecurityTests(unittest.TestCase):
    def tar(self, members):
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w:gz") as archive:
            for name, data, kind in members:
                info = tarfile.TarInfo(name)
                if kind == "file":
                    info.mode = 0o644
                    info.size = len(data)
                    archive.addfile(info, io.BytesIO(data))
                else:
                    info.type = kind
                    info.linkname = str(data)
                    archive.addfile(info)
        return raw.getvalue()

    def canonical(self, extra=(), task=b"task\n", patch=b"diff --git a/a b/a\n"):
        files = [("p/AGENT_TASK.md", task, "file"), ("p/MANIFEST.json", b"{}", "file"),
                 ("p/payload/changes.patch", patch, "file")]
        files.extend(extra)
        sums = []
        for name, data, kind in files:
            if kind == "file":
                sums.append(f"{hashlib.sha256(data).hexdigest()}  {name[2:]}\n".encode())
        files.insert(1, ("p/SHA256SUMS", b"".join(sums), "file"))
        return self.tar(files)

    def assert_extract_rejected(self, data):
        with tempfile.TemporaryDirectory() as raw:
            archive = Path(raw) / "pack.tar.gz"
            archive.write_bytes(data)
            with self.assertRaises(runner.PackError):
                runner.safe_extract(archive, Path(raw) / "out")

    def test_extra_checksummed_and_unchecksummed_files_rejected(self):
        self.assert_extract_rejected(self.canonical([("p/extra", b"x", "file")]))

    def test_missing_canonical_and_invalid_utf8_task_rejected(self):
        self.assert_extract_rejected(self.tar([("p/MANIFEST.json", b"{}", "file"), ("p/SHA256SUMS", b"", "file"), ("p/payload/changes.patch", b"x", "file")]))
        with tempfile.TemporaryDirectory() as raw:
            archive = Path(raw) / "x.tar.gz"; archive.write_bytes(self.canonical(task=b"\xff"))
            root = runner.safe_extract(archive, Path(raw) / "out"); runner.verify_checksums(root)
            with self.assertRaises(runner.PackError): runner.validate_manifest(root)

    def test_links_devices_and_fifo_rejected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            self.assert_extract_rejected(self.canonical([("p/bad", "/tmp/x", kind)]))

    def test_path_and_case_collisions_rejected(self):
        self.assert_extract_rejected(self.tar([("../escape", b"x", "file")]))
        self.assert_extract_rejected(self.tar([("/absolute", b"x", "file")]))
        self.assert_extract_rejected(self.tar([("p/AGENT_TASK.md", b"x", "file"), ("p/agent_task.md", b"y", "file")]))

    def test_checksum_errors_rejected(self):
        data = self.canonical()
        with tempfile.TemporaryDirectory() as raw:
            archive = Path(raw) / "x.tar.gz"; archive.write_bytes(data)
            out = Path(raw) / "out"; root = runner.safe_extract(archive, out)
            (root / "SHA256SUMS").write_text("not-a-checksum\n", encoding="utf-8")
            with self.assertRaises(runner.PackError): runner.verify_checksums(root)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "x.json"; path.write_text('{"a":1,"a":2}', encoding="utf-8")
            with self.assertRaises(ValueError):
                from gpt_patch_pack_v1_common import load_json
                load_json(path)

    def test_compatibility_authorization_contract(self):
        from gpt_patch_pack_v1_common import DEFAULT_COMPATIBILITY, validate_compatibility
        self.assertEqual(validate_compatibility(DEFAULT_COMPATIBILITY), DEFAULT_COMPATIBILITY)
        authorized = {"scope":"legacy-v0","authorized":True,"canonical_implementation":"GPT Patch Pack v1","legacy_behavior":"read-only declaration","authorization_source":"owner:ticket-1","supported_legacy_versions":["v0"],"direction":"forward","removal_condition":"permanent"}
        self.assertEqual(validate_compatibility(authorized), authorized)
        for invalid in ({**authorized, "scope":"none"}, {**authorized, "authorization_source":""}, {**authorized, "supported_legacy_versions":[]}, {**DEFAULT_COMPATIBILITY, "legacy_behavior":"legacy"}):
            with self.assertRaises(ValueError): validate_compatibility(invalid)

    def test_planner_pin_shape_is_strict(self):
        from gpt_patch_pack_v1_common import validate_sha
        with self.assertRaises(ValueError): validate_sha("A" * 40)
        with self.assertRaises(ValueError): validate_sha("0" * 39)

    def test_placeholder_gate_rejected_by_shared_validator(self):
        from gpt_patch_pack_v1_common import validate_manifest
        manifest = {"schema_version":2,"format":"gpt-patch-pack-v1","patch_id":"patch-20260730-120000-security","title":"title","description":"description","created_at":"2026-07-30T12:00:00Z","runner_version":"1.0.0","baseline_release":"v1.3.0","evidence_directory":".gpt-review/evidence/v1.3.0/patch-20260730-120000-security","workflow":{"repository":"https://github.com/rceman/gpt-review-planner","version":"v1.3.0","commit":"0"*40,"document":"GPT_REVIEW_PLANNER.md"},"target":{"repository":"r/r","accepted_origin_urls":["ssh"],"branch":"b","base_revision":"1"*40,"remote":"origin","remote_ref":"refs/remotes/origin/b"},"payload":{"patch":"payload/changes.patch","format":"git-binary-full-index"},"files_created":[],"files_modified":[],"files_deleted":[],"target_tree":"2"*40,"requirements":[{"id":"REQ-001","summary":"s","acceptance":["a"]}],"gates":[{"id":"g","name":"g","kind":"command","argv":["true"],"env":{},"timeout_seconds":1,"max_output_bytes":1024}],"compatibility":{"scope":"none","authorized":False,"canonical_implementation":"GPT Patch Pack v1","legacy_behavior":"unsupported and out of scope","authorization_source":None,"supported_legacy_versions":[],"direction":"none","removal_condition":None},"metadata":{"planner_commit":"0"*40,"gpt_static_checks_performed":[],"gpt_runtime_checks_not_performed":[]}}
        with self.assertRaises(ValueError): validate_manifest(manifest)

    def test_process_group_timeout_is_bounded(self):
        with tempfile.TemporaryDirectory() as raw:
            with self.assertRaisesRegex(runner.PackError, "timed out"):
                runner.run([sys.executable, "-c", "import subprocess,time; subprocess.Popen([\"sleep\",\"5\"]); time.sleep(5)"], Path(raw), timeout=1)

    def test_public_runner_rejects_malicious_payload_before_execution(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw); repo = root / "repo"; repo.mkdir()
            subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
            subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
            marker = root / "executed"
            payload = f"from pathlib import Path; Path({str(marker)!r}).write_text('bad')\n".encode()
            archive = root / "malicious.tar.gz"; archive.write_bytes(self.canonical([("p/payload/apply.py", payload, "file")]))
            digest = hashlib.sha256(archive.read_bytes()).hexdigest()
            result = subprocess.run([sys.executable, str(ROOT / "scripts/gpt-patch-pack-runner-v1.py"), "--archive", str(archive), "--archive-sha256", digest, "--repo", str(repo)], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(marker.exists())

    def test_deterministic_archive_bytes(self):
        spec = importlib.util.spec_from_file_location("builder", ROOT / "scripts/build-gpt-patch-pack-v1.py")
        builder = importlib.util.module_from_spec(spec); assert spec.loader is not None; spec.loader.exec_module(builder)
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "pack"; (root / "payload").mkdir(parents=True)
            (root / "AGENT_TASK.md").write_text("task\n", encoding="utf-8"); (root / "payload/changes.patch").write_bytes(b"patch")
            (root / "MANIFEST.json").write_text("{}\n", encoding="utf-8"); builder.checksums(root)
            one, two = Path(raw) / "one.tgz", Path(raw) / "two.tgz"
            builder.archive(root, one); builder.archive(root, two)
            self.assertEqual(one.read_bytes(), two.read_bytes())


if __name__ == "__main__":
    unittest.main()
