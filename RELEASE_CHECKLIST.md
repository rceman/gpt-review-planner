# Release Checklist

## Initial `v1.0.0`

1. Upload all repository files to `main`.
2. Commit the upload.
3. Confirm GitHub Actions `Validate` passes.
4. Confirm `Build Offline Rust Toolchain` passes.
5. Open that workflow run and confirm artifact `rustc-lite-linux-x86_64` exists.
6. Download the artifact and confirm it contains one `.tar.zst` bundle and one
   matching `.sha256` sidecar.
7. Create and push tag `v1.0.0` from the exact validated commit.
8. Confirm the tag run creates GitHub Release `v1.0.0` and uploads both files.
9. Clone the tagged source and run:

```bash
python -m unittest discover -s tests -v
bash scripts/bootstrap-rustc.sh -- rustc --version
```

10. Test strict offline extraction using the downloaded bundle:

```bash
GPT_RUSTC_NO_NETWORK=1 bash scripts/bootstrap-rustc.sh \
  --force-managed \
  --no-network \
  --cache-dir /tmp/gpt-review-planner-rust \
  --offline-bundle /path/to/rustc-lite-*.tar.zst \
  -- rustc --version
```

11. Verify installation against a disposable project:

```bash
bash setup.sh --project /tmp/test-project --version v1.0.0
```

12. Confirm `AGENTS.md` contains one managed block at the beginning.
13. Confirm `.gpt-workflow.lock` contains the exact 40-character commit SHA.
