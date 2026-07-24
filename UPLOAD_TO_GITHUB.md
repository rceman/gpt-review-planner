# Publish and Release on GitHub

## First publication

1. Create the repository and push the initial `main` branch.
2. Enable the required GitHub Actions workflows and branch protections.
3. Run `python scripts/release.py check` on the exact commit intended for publication.
4. Wait for all required workflows to pass.
5. Create the first annotated release tag with `python scripts/release.py tag`.
6. Push the tag explicitly and verify the generated GitHub Release.

## Subsequent releases

Use [`docs/RELEASE_PROCESS.md`](docs/RELEASE_PROCESS.md) and [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md). The canonical order is:

```text
prepare version files
→ agent quality gates
→ release commit
→ push or merge
→ CI on exact release commit
→ annotated tag
→ explicit tag push
→ GitHub Release verification
```

GitHub Actions validates versions and tags, but it does not choose the next version and does not create hidden version-bump commits.

## Install a published workflow version

```bash
RELEASE_TAG="vX.Y.Z"

bash setup.sh \
  --project /path/to/project \
  --version "$RELEASE_TAG"
```

Projects pin both the tag and its exact commit SHA in `.gpt-workflow.lock`.
