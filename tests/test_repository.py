from __future__ import annotations

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
            ).stdout
            Path(f"{bundle}.sha256").write_text(digest, encoding="utf-8")

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

    def test_template_manifest_is_valid_json(self) -> None:
        path = ROOT / "templates/executable-patch-pack/manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(data["workflow"]["document"], "GPT_REVIEW_PLANNER.md")


if __name__ == "__main__":
    unittest.main()
