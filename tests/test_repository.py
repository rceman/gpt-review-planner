from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FAKE_COMMIT = "a" * 40


class RepositoryTest(unittest.TestCase):
    def test_required_files_exist(self) -> None:
        for relative in (
            "GPT_REVIEW_PLANNER.md",
            "README.md",
            "VERSION",
            "setup.sh",
            "update.sh",
            "scripts/bootstrap-rustc.sh",
            "scripts/build-offline-rust-bundle.sh",
            ".github/workflows/build-offline-rust.yml",
            "toolchains/README.md",
            "docs/FAST_RUSTC_BOOTSTRAP.md",
            "docs/CHATGPT_RUST_SANDBOX_BOOTSTRAP.md",
            "scripts/benchmark-offline-rust.py",
            "scripts/patch_pack_scope.py",
            "templates/executable-patch-pack/DEVIATIONS.md",
            "benchmarks/chatgpt-sandbox-rust-1.97.1.json",
            "schemas/patch-manifest.schema.json",
            "templates/executable-patch-pack/manifest.json",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_setup_is_idempotent_and_preserves_agents_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            original = "# Project agents\n\nExisting instructions.\n"
            (project / "AGENTS.md").write_text(original, encoding="utf-8")

            command = [
                "bash",
                str(ROOT / "setup.sh"),
                "--project",
                str(project),
                "--version",
                "v1.0.0",
                "--commit",
                FAKE_COMMIT,
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)
            subprocess.run(command, check=True, capture_output=True, text=True)

            agents = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertTrue(agents.startswith("<!-- BEGIN GPT-REVIEW-PLANNER -->"))
            self.assertEqual(agents.count("<!-- BEGIN GPT-REVIEW-PLANNER -->"), 1)
            self.assertIn(original.strip(), agents)

            lock = json.loads(
                (project / ".gpt-workflow.lock").read_text(encoding="utf-8")
            )
            self.assertEqual(lock["commit"], FAKE_COMMIT)
            self.assertEqual(lock["version"], "v1.0.0")

    def test_update_replaces_pin_without_duplicate_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            first_commit = "a" * 40
            second_commit = "b" * 40

            subprocess.run(
                [
                    "bash",
                    str(ROOT / "setup.sh"),
                    "--project",
                    str(project),
                    "--version",
                    "v1.0.0",
                    "--commit",
                    first_commit,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            subprocess.run(
                [
                    "bash",
                    str(ROOT / "update.sh"),
                    "--project",
                    str(project),
                    "--version",
                    "v1.1.0",
                    "--commit",
                    second_commit,
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            agents = (project / "AGENTS.md").read_text(encoding="utf-8")
            self.assertEqual(agents.count("<!-- BEGIN GPT-REVIEW-PLANNER -->"), 1)
            self.assertIn(second_commit, agents)
            self.assertNotIn(first_commit, agents)

            lock = json.loads(
                (project / ".gpt-workflow.lock").read_text(encoding="utf-8")
            )
            self.assertEqual(lock["version"], "v1.1.0")
            self.assertEqual(lock["commit"], second_commit)

    def test_setup_supports_nested_agents_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            subprocess.run(
                [
                    "bash",
                    str(ROOT / "setup.sh"),
                    "--project",
                    str(project),
                    "--agents-file",
                    "docs/AGENTS.md",
                    "--commit",
                    FAKE_COMMIT,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            nested_agents = project / "docs/AGENTS.md"
            self.assertTrue(nested_agents.is_file())
            self.assertIn("](../.gpt-workflow.lock)", nested_agents.read_text(encoding="utf-8"))

    def test_setup_rejects_malformed_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project = Path(temp_dir)
            (project / "AGENTS.md").write_text(
                "<!-- BEGIN GPT-REVIEW-PLANNER -->\nExisting content\n",
                encoding="utf-8",
            )

            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "setup.sh"),
                    "--project",
                    str(project),
                    "--commit",
                    FAKE_COMMIT,
                ],
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("malformed or duplicate", result.stderr)

    def test_bootstrap_rustc_reuses_existing_compiler(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_bin = Path(temp_dir) / "bin"
            fake_bin.mkdir()
            fake_rustc = fake_bin / "rustc"
            fake_rustc.write_text(
                "#!/usr/bin/env bash\nprintf 'rustc 9.9.9-test\n'\n",
                encoding="utf-8",
            )
            fake_rustc.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/bootstrap-rustc.sh"),
                    "--project",
                    str(ROOT),
                    "--",
                    "rustc",
                    "--version",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertEqual(result.stdout.strip(), "rustc 9.9.9-test")
            self.assertIn("reusing existing compiler", result.stderr)

    def test_bootstrap_rustc_managed_install_and_cache_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fake_bin = temp / "fake-bin"
            cache = temp / "cache"
            fake_bin.mkdir()

            installer_source = temp / "fake-rustup-init"
            installer_source.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
mkdir -p "$CARGO_HOME/bin" "$RUSTUP_HOME"
cat > "$CARGO_HOME/bin/rustup" <<'INNER'
#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "run" ]]; then
  printf 'rustc 1.96.0-fake\\n'
  exit 0
fi
if [[ "${1:-}" == "toolchain" && "${2:-}" == "install" ]]; then
  exit 0
fi
exit 1
INNER
cat > "$CARGO_HOME/bin/rustc" <<'INNER'
#!/usr/bin/env bash
printf 'rustc 1.96.0-fake\\n'
INNER
chmod +x "$CARGO_HOME/bin/rustup" "$CARGO_HOME/bin/rustc"
""",
                encoding="utf-8",
            )
            installer_source.chmod(0o755)

            fake_curl = fake_bin / "curl"
            fake_curl.write_text(
                """#!/usr/bin/env bash
set -euo pipefail
output=''
url=''
while (($# > 0)); do
  case "$1" in
    --output) output="$2"; shift 2 ;;
    http*) url="$1"; shift ;;
    *) shift ;;
  esac
done
[[ -n "$output" && -n "$url" ]]
if [[ "$url" == *.sha256 ]]; then
  sha256sum "$FAKE_RUSTUP_INSTALLER" | awk '{print $1}' > "$output"
else
  cp "$FAKE_RUSTUP_INSTALLER" "$output"
fi
""",
                encoding="utf-8",
            )
            fake_curl.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            env["FAKE_RUSTUP_INSTALLER"] = str(installer_source)

            command = [
                "bash",
                str(ROOT / "scripts/bootstrap-rustc.sh"),
                "--project",
                str(ROOT),
                "--cache-dir",
                str(cache),
                "--toolchain",
                "1.96.0",
                "--force-managed",
            ]
            first = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(first.stdout.strip(), "rustc 1.96.0-fake")
            self.assertIn("downloading official rustup-init", first.stderr)

            fake_curl.write_text(
                "#!/usr/bin/env bash\nexit 99\n", encoding="utf-8"
            )
            second = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(second.stdout.strip(), "rustc 1.96.0-fake")
            self.assertIn("reusing cached toolchain", second.stderr)


    def test_bootstrap_rustc_offline_bundle_and_cache_reuse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            cache = temp / "cache"
            stage = temp / "stage"
            host = "x86_64-unknown-linux-gnu"
            bundle_name = f"rustc-lite-9.9.9-test-{host}"
            root = stage / bundle_name
            (root / "bin").mkdir(parents=True)

            for name, output in (("rustc", "rustc 9.9.9-offline"), ("cargo", "cargo 9.9.9-offline")):
                executable = root / "bin" / name
                executable.write_text(
                    f"#!/usr/bin/env bash\nprintf '{output}\\n'\n",
                    encoding="utf-8",
                )
                executable.chmod(0o755)

            (root / "manifest.json").write_text(
                json.dumps({"host": host, "rust_release": "9.9.9-test"}),
                encoding="utf-8",
            )
            bundle = temp / f"{bundle_name}.tar.zst"
            subprocess.run(
                ["tar", "--zstd", "-cf", str(bundle), "-C", str(stage), bundle_name],
                check=True,
                capture_output=True,
                text=True,
            )
            digest = subprocess.run(
                ["sha256sum", str(bundle)],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.split()[0]
            Path(f"{bundle}.sha256").write_text(
                f"{digest}  {bundle.name}\n", encoding="utf-8"
            )
            subprocess.run(
                ["sha256sum", "-c", Path(f"{bundle}.sha256").name],
                cwd=temp,
                check=True,
                capture_output=True,
                text=True,
            )

            command = [
                "bash",
                str(ROOT / "scripts/bootstrap-rustc.sh"),
                "--project",
                str(ROOT),
                "--cache-dir",
                str(cache),
                "--force-managed",
                "--no-network",
                "--offline-bundle",
                str(bundle),
                "--",
                "rustc",
                "--version",
            ]
            first = subprocess.run(
                command, check=True, capture_output=True, text=True
            )
            self.assertEqual(first.stdout.strip(), "rustc 9.9.9-offline")
            self.assertIn("offline-bundle", first.stderr)

            bundle.unlink()
            Path(f"{bundle}.sha256").unlink()
            second = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/bootstrap-rustc.sh"),
                    "--project",
                    str(ROOT),
                    "--cache-dir",
                    str(cache),
                    "--force-managed",
                    "--no-network",
                    "--",
                    "rustc",
                    "--version",
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertEqual(second.stdout.strip(), "rustc 9.9.9-offline")
            self.assertIn("offline-cache", second.stderr)

    def test_bootstrap_rejects_bash_login_shell(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_bin = Path(temp_dir) / "bin"
            fake_bin.mkdir()
            fake_rustc = fake_bin / "rustc"
            fake_rustc.write_text(
                "#!/usr/bin/env bash\nprintf 'rustc 9.9.9-test\n'\n",
                encoding="utf-8",
            )
            fake_rustc.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/bootstrap-rustc.sh"),
                    "--",
                    "bash",
                    "-lc",
                    "rustc --version",
                ],
                capture_output=True,
                text=True,
                env=env,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Use 'bash -c' instead of 'bash -lc'", result.stderr)

    def test_bootstrap_rejects_login_shell_after_other_bash_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            fake_bin = Path(temp_dir) / "bin"
            fake_bin.mkdir()
            fake_rustc = fake_bin / "rustc"
            fake_rustc.write_text(
                "#!/usr/bin/env bash\nprintf 'rustc 9.9.9-test\n'\n",
                encoding="utf-8",
            )
            fake_rustc.chmod(0o755)

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            cases = (
                ["bash", "-O", "extglob", "-lc", "rustc --version"],
                ["bash", "-o", "pipefail", "-lc", "rustc --version"],
                ["bash", "--norc", "-lc", "rustc --version"],
            )
            for command in cases:
                with self.subTest(command=command):
                    result = subprocess.run(
                        ["bash", str(ROOT / "scripts/bootstrap-rustc.sh"), "--", *command],
                        capture_output=True,
                        text=True,
                        env=env,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("Use 'bash -c' instead of 'bash -lc'", result.stderr)

    def test_bootstrap_does_not_treat_script_arguments_as_bash_options(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            fake_bin = temp / "bin"
            fake_bin.mkdir()
            fake_rustc = fake_bin / "rustc"
            fake_rustc.write_text(
                "#!/usr/bin/env bash\nprintf 'rustc 9.9.9-test\n'\n",
                encoding="utf-8",
            )
            fake_rustc.chmod(0o755)
            script = temp / "check.sh"
            script.write_text("rustc --version\n", encoding="utf-8")

            env = os.environ.copy()
            env["PATH"] = f"{fake_bin}:{env['PATH']}"
            result = subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/bootstrap-rustc.sh"),
                    "--",
                    "bash",
                    str(script),
                    "-l",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(result.stdout.strip(), "rustc 9.9.9-test")

    def test_no_executable_bootstrap_example_uses_login_shell(self) -> None:
        for path in ROOT.rglob("*"):
            if not path.is_file() or path.suffix not in {".md", ".yml", ".yaml", ".sh"}:
                continue
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("-- bash -lc", text, str(path.relative_to(ROOT)))

    def test_benchmark_accepts_legacy_absolute_path_sidecar(self) -> None:
        script = ROOT / "scripts/benchmark-offline-rust.py"
        spec = importlib.util.spec_from_file_location("benchmark_offline_rust", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp_dir:
            bundle = Path(temp_dir) / "rustc-lite-test.tar.zst"
            bundle.write_bytes(b"legacy-sidecar-test")
            digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
            Path(f"{bundle}.sha256").write_text(
                f"{digest}  /home/runner/work/repo/dist/{bundle.name}\n",
                encoding="utf-8",
            )
            self.assertEqual(module.verify_bundle(bundle), digest)

    def test_release_builder_declares_portable_metadata(self) -> None:
        script = (ROOT / "scripts/build-offline-rust-bundle.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("rustc-lite-manifest.json", script)
        self.assertIn("archive_basename", script)
        self.assertIn("printf '%s  %s\\n'", script)

        workflow = (ROOT / ".github/workflows/build-offline-rust.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn("sha256sum -c ./*.sha256", workflow)
        self.assertIn("hashlib.sha256()", workflow)
        self.assertIn('manifest["sha256"] == digest.hexdigest()', workflow)
        self.assertIn('manifest["size_bytes"] == bundle.stat().st_size', workflow)
        self.assertIn("dist/*.json", workflow)

    def _write_scope_pack(
        self,
        root: Path,
        *,
        base_revision: str,
        modified: list[str] | None = None,
        created: list[str] | None = None,
        deleted: list[str] | None = None,
        patch_paths: list[str] | None = None,
        overlay_paths: list[str] | None = None,
    ) -> None:
        (root / "patch").mkdir(parents=True)
        (root / "overlay").mkdir()
        (root / "scripts").mkdir()
        modified = modified or []
        created = created or []
        deleted = deleted or []
        patch_paths = patch_paths or []
        overlay_paths = overlay_paths or []
        manifest = {
            "patch_id": "TEST-SCOPE",
            "workflow": {
                "repository": "https://github.com/rceman/gpt-review-planner",
                "version": "v1.0.1",
                "commit": FAKE_COMMIT,
                "document": "GPT_REVIEW_PLANNER.md",
            },
            "target": {
                "repository": "test/repository",
                "branch": "test",
                "base_revision": base_revision,
            },
            "files_created": created,
            "files_modified": modified,
            "files_deleted": deleted,
            "locally_validated": [],
            "requires_agent_validation": [],
            "known_integration_risks": [],
            "forbidden_deviations": [],
            "required_quality_gates": [],
        }
        (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        patch = "".join(
            f"diff --git a/{path} b/{path}\n"
            "index 3367afd..3e75765 100644\n"
            f"--- a/{path}\n"
            f"+++ b/{path}\n"
            "@@ -1 +1 @@\n"
            "-old\n"
            "+new\n"
            for path in patch_paths
        )
        (root / "patch/changes.patch").write_text(patch, encoding="utf-8")
        (root / "patch/delete-paths.txt").write_text(
            "".join(f"{path}\n" for path in deleted),
            encoding="utf-8",
        )
        for relative in overlay_paths:
            target = root / "overlay" / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("new\n", encoding="utf-8")
        (root / "DEVIATIONS.md").write_text(
            "# Agent Deviations\n\nStatus: none\n\nNo deviations.\n",
            encoding="utf-8",
        )
        scope_script = ROOT / "scripts/patch_pack_scope.py"
        target_script = root / "scripts/patch_pack_scope.py"
        target_script.write_text(scope_script.read_text(encoding="utf-8"), encoding="utf-8")

    def test_patch_pack_scope_rejects_payload_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            pack = Path(temp_dir) / "pack"
            pack.mkdir()
            self._write_scope_pack(
                pack,
                base_revision=FAKE_COMMIT,
                modified=["a.txt", "b.txt"],
                patch_paths=["a.txt"],
                overlay_paths=["a.txt"],
            )
            result = subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/patch_pack_scope.py"),
                    "validate-pack",
                    str(pack),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("missing=b.txt", result.stderr)

    def test_patch_pack_scope_verifies_exact_final_diff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repository = temp / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
            (repository / "a.txt").write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "a.txt"], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-qm", "base"], check=True)
            base = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            (repository / "a.txt").write_text("new\n", encoding="utf-8")

            pack = temp / "pack"
            pack.mkdir()
            self._write_scope_pack(
                pack,
                base_revision=base,
                modified=["a.txt"],
                patch_paths=["a.txt"],
                overlay_paths=["a.txt"],
            )
            command = [
                "python3",
                str(ROOT / "scripts/patch_pack_scope.py"),
                "verify-result",
                str(pack),
                str(repository),
            ]
            subprocess.run(command, check=True, capture_output=True, text=True)

            (repository / "b.txt").write_text("undeclared\n", encoding="utf-8")
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("extra=b.txt", result.stderr)

    def test_patch_pack_scope_accepts_unicode_and_space_patch_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repository = temp / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
            paths = ["docs/Привет.md", "docs/file with spaces.md", "docs/Привет file.md"]
            for relative in paths:
                target = repository / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-qm", "base"], check=True)
            for relative in paths:
                (repository / relative).write_text("new\n", encoding="utf-8")
            patch = subprocess.run(
                ["git", "-C", str(repository), "diff", "--binary", "HEAD", "--"],
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

            pack = temp / "pack"
            pack.mkdir()
            self._write_scope_pack(
                pack,
                base_revision=FAKE_COMMIT,
                modified=paths,
                overlay_paths=paths,
            )
            (pack / "patch/changes.patch").write_bytes(patch)
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/patch_pack_scope.py"),
                    "validate-pack",
                    str(pack),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

    def test_patch_pack_scope_rejects_wrong_final_operation_types(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repository = temp / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
            (repository / "a.txt").write_text("old\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "a.txt"], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-qm", "base"], check=True)
            base = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            cases = (
                ("declared-modified-actual-deleted", {"modified": ["a.txt"]}, "delete"),
                ("declared-created-actual-modified", {"created": ["a.txt"]}, "modify"),
            )
            for name, declaration, operation in cases:
                with self.subTest(name=name):
                    subprocess.run(["git", "-C", str(repository), "reset", "--hard", "-q", base], check=True)
                    if operation == "delete":
                        (repository / "a.txt").unlink()
                    else:
                        (repository / "a.txt").write_text("new\n", encoding="utf-8")
                    pack = temp / name
                    pack.mkdir()
                    self._write_scope_pack(
                        pack,
                        base_revision=base,
                        patch_paths=["a.txt"],
                        overlay_paths=["a.txt"],
                        **declaration,
                    )
                    result = subprocess.run(
                        [
                            "python3",
                            str(ROOT / "scripts/patch_pack_scope.py"),
                            "verify-result",
                            str(pack),
                            str(repository),
                        ],
                        capture_output=True,
                        text=True,
                    )
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("final ", result.stderr)
                    self.assertIn("scope mismatch", result.stderr)

    def test_patch_pack_scope_accepts_rename_as_delete_plus_create(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            repository = temp / "repository"
            repository.mkdir()
            subprocess.run(["git", "init", "-q", str(repository)], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repository), "config", "user.name", "Test"], check=True)
            (repository / "old.txt").write_text("same\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repository), "add", "old.txt"], check=True)
            subprocess.run(["git", "-C", str(repository), "commit", "-qm", "base"], check=True)
            base = subprocess.run(
                ["git", "-C", str(repository), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(["git", "-C", str(repository), "mv", "old.txt", "new.txt"], check=True)

            pack = temp / "pack"
            pack.mkdir()
            self._write_scope_pack(
                pack,
                base_revision=base,
                created=["new.txt"],
                deleted=["old.txt"],
                patch_paths=["new.txt"],
                overlay_paths=["new.txt"],
            )
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "scripts/patch_pack_scope.py"),
                    "verify-result",
                    str(pack),
                    str(repository),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

    def test_patch_pack_scope_maps_copy_status_to_created(self) -> None:
        script = ROOT / "scripts/patch_pack_scope.py"
        spec = importlib.util.spec_from_file_location("patch_pack_scope", script)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        created, modified, deleted = module.parse_name_status(
            b"C100\0source.txt\0copy.txt\0"
        )
        self.assertEqual(created, {"copy.txt"})
        self.assertEqual(modified, set())
        self.assertEqual(deleted, set())

    def test_new_patch_pack_includes_scope_verifier_and_deviation_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            subprocess.run(
                [
                    "bash",
                    str(ROOT / "scripts/new-patch-pack.sh"),
                    "TEST-PACK",
                    temp_dir,
                ],
                check=True,
                capture_output=True,
                text=True,
            )
            pack = Path(temp_dir) / "TEST-PACK"
            self.assertTrue((pack / "DEVIATIONS.md").is_file())
            self.assertTrue((pack / "scripts/patch_pack_scope.py").is_file())

    def test_observed_benchmark_fixture_is_valid(self) -> None:
        data = json.loads(
            (ROOT / "benchmarks/chatgpt-sandbox-rust-1.97.1.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(data["source"]["workflow_run_id"], 29910237409)
        self.assertEqual(data["rust"]["version"], "1.97.1")
        self.assertEqual(len(data["samples"]), 5)
        self.assertGreater(data["median"]["cold_bootstrap_compile_test_seconds"], 0)
        self.assertGreater(data["median"]["warm_cache_compile_test_seconds"], 0)

    def test_template_manifest_is_valid_json(self) -> None:
        path = ROOT / "templates/executable-patch-pack/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["workflow"]["document"], "GPT_REVIEW_PLANNER.md")


if __name__ == "__main__":
    unittest.main()
