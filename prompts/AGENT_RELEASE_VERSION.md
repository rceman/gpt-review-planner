# Release Version

Release this repository as `<TARGET_VERSION>`.

Write all execution communication and the final report in English regardless
of the language used by the owner. Preserve exact version strings, commands,
paths, refs, tags, CI output, and error messages without translation. Do not
duplicate instructions or reports bilingually. Follow
`docs/AGENT_COMMUNICATION_LANGUAGE.md`.

Before changing anything, read and follow `docs/RELEASE_LIFECYCLE.md` and
`docs/RELEASE_PROCESS.md` completely. The task-specific handoff must contain
exactly one `Release lifecycle mode: implementation_unreleased` or `Release
lifecycle mode: release_publication` declaration and one `Release target
version: X.Y.Z` declaration.

For a runtime-affecting release also read `docs/RUNTIME_UPGRADE_POLICY.md` and
`docs/PERSISTED_STATE_MIGRATION_POLICY.md`; validate the declared upgrade task
before release mutation and prove installed and running versions separately.

Read `docs/HOST_PREREQUISITES.md` before release mutation and verify:

```bash
python3 -m pytest --version
```

Use only:

- `scripts/release.py`
- `release-config.json`

For `implementation_unreleased`, run only the source-state gate:

```bash
python3 scripts/release.py check-source
```

Do not create a dated heading, release commit, tag, or publication in that
mode. For `release_publication`, first validate the explicit declaration with:

```bash
python3 scripts/validate-release-publication.py \
  <PROJECT>/release-publication.json \
  --repo <PROJECT>
```

Then use the ordered canonical commands from `docs/RELEASE_LIFECYCLE.md`:
`prepare`, `check-release-ready`, `commit`, exact release-commit CI,
`check-tag-ready`, `tag`, and `verify-tag`. After `verify-tag`, push exactly:

```bash
git push origin refs/tags/v<TARGET_VERSION>:refs/tags/v<TARGET_VERSION>
```

Derive post-tag proofs only from the validated declaration. `workflow: null`
means no post-tag CI; a declared workflow requires the exact name, path, tag
selection, event, and created-after baseline in its tag-CI gate, followed by
`scripts/verify-release-publication.py`. `github_actions` additionally expects
the declared GitHub Release and assets; `tag_only` must not claim them. The
agent never creates or updates a Release, calls a publication API, discovers
credentials, or uses local `gh`, curl, wget, `GH_TOKEN`, or `GITHUB_TOKEN`.

If the project contains `scripts/release.py`, prove planner conformance with:

```bash
python3 scripts/validate-release-tool-conformance.py \
  --release-script scripts/release.py \
  --ci-script scripts/check-github-ci.py
```

For every required remote-CI gate, use the exact checked-out commit:

```bash
python3 scripts/check-github-ci.py \
  --repository OWNER/REPO \
  --sha-from-git HEAD \
  --policy required \
  --wait \
  --format json
```

The owner has selected `<TARGET_VERSION>`. Do not select or infer another
version. Do not manually edit synchronized version files, bypass required
gates, force-push, rewrite published history, push all tags, or publish a
GitHub Release unless explicitly authorized.

Do not broaden the task scope. Return the final report required by the release
runbook, including local gates, CI evidence, tag verification, and final remote
identity checks.
Apply the resolved CI capability policy. Remote CI is not universal; local runtime gates remain mandatory when CI is unavailable or disabled.
Use the compact reporting contract: one `Release CI` record and one `Tag CI` record. After a terminal status, consult `docs/PROCEDURE_INDEX.md` and emit the next-transition handoff.
