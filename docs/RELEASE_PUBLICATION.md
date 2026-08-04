# Release Publication Contract

`release-publication.json` is a project-local, strict declaration of release
side effects and their proofs. It is required for an integrated project and is
validated by `scripts/validate-release-publication.py`; the declaration is not
created at this planner repository root by this task.

There are exactly three modes:

* `none`: no tag-triggered workflow, GitHub Release, asset publication, or
  local publication credential is authorized. The exact form is
  `{"schema_version":1,"mode":"none"}`.
* `tag_only`: an annotated tag is pushed. A workflow is optional but must be
  explicit: `workflow: null` means no CI is declared and requires
  `proof_requirements.tag_ci=false` and
  `proof_requirements.distinct_post_tag_workflow=false`; an object requires the
  complete workflow identity and both proofs to be true.
* `github_actions`: a complete workflow declaration is required. The workflow
  creates or updates the GitHub Release using `github.token`; asset behavior is
  declared separately.

Active declarations bind the exact tag pattern, annotated-tag source, workflow
path/name/digest, `push` event, tag trigger (`explicit_tags_filter` or
`unfiltered_push`), contents permission, distinct-run requirement, and
created-after-tag-push baseline. The workflow scanner is bounded, UTF-8,
standard-library-only, and rejects a digest or name that does not match the
declared file. It does not infer omitted fields.

Asset declarations separate `workflow_source_patterns` (for example,
`dist/*`, checked statically against workflow commands) from
`published_name_patterns` (asset basenames, checked against the read-only
publication response). `assets.policy` is exactly `none` or
`workflow_produced`. Release notes use a strict `notes` object with source
`none`, `generated`, `changelog`, or `declared_file` (the last requires a
repository-relative `file`). Automatic effects are named `tag_ci`,
`github_release_create_or_update`, and `asset_upload`; `annotated_tag_push` is
not an automatic effect.

The read-only verifier
`python3 scripts/verify-release-publication.py` validates the annotated tag,
selects the declared workflow by exact name and path, exact tag head SHA,
`head_branch`, event, and a concrete RFC3339 `--created-after` baseline, then
checks jobs and (for `github_actions`) Release metadata and published asset
basenames. It uses only GET requests and loopback-testable REST responses.
It never creates releases, uploads assets, discovers credentials, or mutates
repository state.

The lifecycle gate order is fixed:

```text
conformance → prepare → check-release-ready → commit → release-commit CI
→ check-tag-ready → tag → verify-tag
→ git push origin refs/tags/vT:refs/tags/vT
→ declared tag/publication CI (when workflow is an object) → publication verifier
```

`release-commit CI` remains the existing canonical exact-SHA gate. A declared
tag/publication workflow uses exact workflow name and path, exact tag/ref
selection, exact event, a parsed RFC3339 baseline, and a distinct run. A
`workflow: null` declaration has no CI gate. Publication tasks are rejected
when the project declaration is `none`, and local `gh`, REST, curl, wget, or
credential commands are never valid substitutes for the read-only verifier.

Project conformance compares the project copies of release, CI, publication
validator, and publication verifier tools byte-for-byte with the planner
canonical copies and checks their advertised interfaces. The project state
gate runs through the project's `scripts/release.py`; conformance uses the
planner's canonical release script as its reference.

This contract describes publication declaration and proof only. Release
mutation, tag creation, GitHub Release authorization, installation, running,
activation, and connector changes remain separate explicitly authorized tasks.
