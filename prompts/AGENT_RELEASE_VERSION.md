# Release Version

Release this repository as `<TARGET_VERSION>`.

Before changing anything, read and follow `docs/RELEASE_PROCESS.md` completely.

Use only:

- `scripts/release.py`
- `release-config.json`

The owner has selected `<TARGET_VERSION>`. Do not select or infer another
version. Do not manually edit synchronized version files, bypass required
gates, force-push, rewrite published history, push all tags, or publish a
GitHub Release unless explicitly authorized.

Do not broaden the task scope. Return the final report required by the release
runbook, including local gates, CI evidence, tag verification, and final remote
identity checks.
