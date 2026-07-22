# Offline Rust toolchains

Compiler binaries are not committed to Git.

GitHub Actions produces versioned `rustc-lite-*.tar.zst` bundles and SHA-256
sidecars. A downloaded bundle may be placed in this directory; then
`scripts/bootstrap-rustc.sh` discovers it automatically.

Artifacts contain the official Rust minimal toolchain components:

- `rustc`
- `rust-std`
- `cargo`

The source repository remains small while uploaded project or patch archives can
include a bundle when a truly network-free sandbox is required.
