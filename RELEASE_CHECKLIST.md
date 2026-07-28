# Release Checklist

All executable gates belong to the local coding agent. GPT performs static/artifact review and reviews committed agent evidence without rerunning tests.

## Prepare the release commit

1. Start from the exact approved branch and confirm the worktree is clean.
2. Select the intended semantic version.
3. Update every configured version-bearing file through the canonical script:

```bash
python scripts/release.py prepare X.Y.Z
python scripts/release.py check
git diff --check
```

4. Review the version diff. Do not edit version-bearing files manually. A
   feature patch may carry an owner-approved minor-version change only when the
   approved scope explicitly includes the new public contract; merge, exact-SHA
   CI, and evidence still precede tagging.
5. Run every repository quality gate required by the patch and project.
6. Create the release commit:

```bash
python scripts/release.py commit
```

7. Push the release commit or merge its pull request.
8. Wait for required CI workflows to pass on the exact release commit.

## Create the release tag

9. Check out the validated release commit on the release branch, normally `main`.
10. Confirm the worktree is clean and version consistency still passes:

```bash
python scripts/release.py check
```

11. Create the annotated tag:

```bash
python scripts/release.py tag
```

12. Push the tag explicitly:

```bash
RELEASE_TAG="v$(cat VERSION)"
git push origin "$RELEASE_TAG"
```

13. Confirm the tag workflow runs:

```bash
python scripts/release.py verify-tag "$RELEASE_TAG"
```

14. Verify the GitHub Release and all expected artifacts, checksums, and provenance metadata.
15. Record the release commit, tag, CI run, and release URL in the release evidence.

## Prohibited release shortcuts

- Do not place a concrete current version in `README.md`.
- Do not manually edit one version file without synchronizing the configured set.
- Do not create a tag before CI passes on the release commit.
- Do not force-move or replace a published release tag.
- Do not let GitHub Actions silently invent or increment a version.
- Do not combine implementation changes and a release-only version bump unless the approved patch explicitly requires it.
