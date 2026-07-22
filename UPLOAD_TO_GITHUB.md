# Upload and First Release

Target repository:

```text
https://github.com/rceman/gpt-review-planner
```

## 1. Upload source

1. Extract `gpt-review-planner-v1.0.0.zip` locally.
2. Open the extracted `gpt-review-planner-v1.0.0` directory.
3. In the GitHub repository, choose **Add file → Upload files**.
4. Upload the directory contents, not the outer directory itself.
5. Confirm these hidden/configuration paths are included:
   - `.github/workflows/validate.yml`;
   - `.github/workflows/build-offline-rust.yml`;
   - `.gitignore`;
   - `.editorconfig`.
6. Commit directly to `main` with a message such as:

```text
Initial GPT Review Planner v1.0.0
```

## 2. Verify GitHub Actions

Open the repository **Actions** tab and wait for both workflows:

```text
Validate
Build Offline Rust Toolchain
```

Both must be green.

Open the successful `Build Offline Rust Toolchain` run and confirm the artifact:

```text
rustc-lite-linux-x86_64
```

The artifact ZIP must contain:

```text
rustc-lite-<resolved-version>-x86_64-unknown-linux-gnu.tar.zst
rustc-lite-<resolved-version>-x86_64-unknown-linux-gnu.tar.zst.sha256
```

## 3. Publish `v1.0.0`

Using github.com:

1. Open **Releases**.
2. Choose **Draft a new release**.
3. Choose **Create new tag** and enter `v1.0.0`.
4. Target the validated `main` commit.
5. Set release title to `v1.0.0`.
6. Publish the release.

The tag triggers `Build Offline Rust Toolchain` again. The workflow detects the
existing release and uploads or replaces the Rust bundle and SHA-256 sidecar.

After the tag workflow succeeds, refresh the release and confirm both assets are
attached.

## 4. Request GPT verification

Send GPT:

```text
Verify https://github.com/rceman/gpt-review-planner after the v1.0.0 release.
Check both workflows, download the rustc-lite artifact, measure cold and warm
bootstrap, and run the standalone Rust tests in the sandbox.
```

GPT can inspect the workflow run and download its artifact through the connected
GitHub integration.
