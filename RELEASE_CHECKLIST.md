# Release Checklist

## Patch release `v1.0.1`

1. Apply the final pre-release correction patch to the merged `main` base commit:

```text
56395da967151bb71d8596d8498be8ecfc811eac
```

2. Run local static and unit gates:

```bash
bash -n setup.sh update.sh scripts/*.sh
python -m compileall scripts tests examples
python -m unittest discover -s tests -v
python -m unittest discover -s examples/rust-domain-feature/reference/python -v
```

3. Confirm the login-shell guard rejects `-lc` even after `-O`, `-o`, and
   long Bash options, while ordinary script arguments remain allowed.
4. Confirm generated patch packs contain `DEVIATIONS.md` and reject any final
   repository path outside `manifest.json`.
5. Confirm `changes.patch` validation accepts UTF-8 paths, spaces, and their
   combination without relying on quoted `diff --git` header parsing.
6. Confirm final-result validation distinguishes created, modified, and deleted
   operations and maps rename/copy statuses according to the documented contract.
7. Commit and merge the validated patch to `main`.
8. Confirm GitHub Actions `Validate` passes.
9. Confirm `Build Offline Rust Toolchain` passes.
10. Open the successful toolchain run and verify artifact
    `rustc-lite-linux-x86_64` contains exactly:

```text
rustc-lite-<resolved-version>-x86_64-unknown-linux-gnu.tar.zst
rustc-lite-<resolved-version>-x86_64-unknown-linux-gnu.tar.zst.sha256
rustc-lite-manifest.json
```

11. Confirm the sidecar is portable:

```bash
cd /path/to/extracted/artifact
sha256sum -c rustc-lite-*.sha256
```

12. Run the dependency-free benchmark helper:

```bash
python scripts/benchmark-offline-rust.py \
  --artifact-zip /path/to/rustc-lite-linux-x86_64.zip
```

13. Confirm the benchmark proves:
    - checksum verification;
    - strict zero-network cold extraction;
    - `rustc` and `cargo` availability;
    - standalone Rust compilation;
    - all Rust tests pass;
    - warm-cache reuse.
14. Create and push tag `v1.0.1` from the exact validated `main` commit.
15. Confirm the tag workflow creates or updates Release `v1.0.1` and attaches
    all three files.
16. Record the successful Actions run URL in release notes so ChatGPT can fetch
    the artifact through the connected GitHub integration.
17. Update one disposable project pin:

```bash
bash update.sh --project /tmp/test-project --version v1.0.1
```

18. Confirm `.gpt-workflow.lock` contains tag `v1.0.1` and its exact commit SHA.

## Historical initial release `v1.0.0`

The initial release established the repository, workflows, setup/update scripts,
and the first offline Rust artifact. It remains useful only as a regression input
for proving that `v1.0.1` can verify legacy absolute-path checksum sidecars.
