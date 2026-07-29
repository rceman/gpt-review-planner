# Committed Agent Evidence

## Directory identity

Every new executable patch pack declares one immutable evidence directory:

```text
.gpt-review/evidence/<baseline-release>/patch-<UTC-YYYYMMDD-HHMMSS>-<slug>/
```

The timestamp is assigned when GPT creates the manifest. `baseline-release` is the last published target-repository tag used as the logical patch baseline; it is not inferred from an unreleased version file.

## Canonical evidence files

The evidence-only commit contains exactly:

```text
manifest.json
evidence.json
```

`manifest.json` is copied byte-for-byte from the patch pack. It defines identity, target base, expected file-operation scope, requirements, acceptance criteria, and required gates.

`evidence.json` is compact and contains only facts that cannot be recovered from the manifest or Git:

```json
{
  "schema_version": 1,
  "implementation_commit": "<40-char-sha>",
  "requirements": [],
  "gates": [],
  "deviations": []
}
```

It does not repeat patch title, commands, expected scope, or evidence commit SHA.

## Requirement proofs

Every manifest requirement has a stable ID. A passing evidence entry cites one or more verifiable proofs:

- `source`, `test`, `workflow`, or `documentation`: repository path, inclusive line range, exact snippet SHA-256, and optional symbol;
- `json`: repository path, JSON pointer, and expected value;
- `deletion`: path that existed in the base commit and is absent from the implementation commit.

Text proof ranges are limited to 160 lines. The checker loads the cited file from the validated implementation commit, hashes the exact selected bytes, and verifies the optional symbol occurs inside the cited range.

## Compact gate results

A required gate whose executable or module is missing is not `pass`; a missing required runner is an environment prerequisite failure. `No module named pytest` is an environment prerequisite failure: restore or install the prerequisite and rerun the gate, or report a blocker before creating committed evidence. Evidence preparation and the evidence commit wait until every required gate has executed successfully. A gate summary must not use `status: pass` while stating that part of the required suite was unavailable or skipped.

This is invalid because status and summary contradict each other:

```json
{
  "id": "local-gates",
  "status": "pass",
  "summary": "All gates passed; pytest was unavailable."
}
```

A valid completed result is:

```json
{
  "id": "local-gates",
  "status": "pass",
  "summary": "Unit, pytest, oracle, shell, compile, validator, release, and diff gates passed."
}
```

Gate commands and expectations live only in `manifest.json`. `evidence.json` records compact results by gate ID:

```json
{"id":"unit","status":"pass","exit":0,"tests":47,"summary":"Ran 47 tests ... OK"}
```

GitHub Actions gates use run/job IDs and a URL. Only implementation-commit CI
may be a committed gate. CI for the evidence commit or later PR heads is
post-commit metadata and is reported externally; it is not stored in
`manifest.json` or `evidence.json`. The checker requires every valid manifest
gate exactly once and rejects failed or skipped required gates.

## Deviations

Deviations are embedded in `evidence.json`; there is no separate Markdown deviation report. The presence of an entry means it is documented. The owner-approved manifest-correction deviation may set `scope_changed` to `true`; all other accepted deviations must preserve declared scope and behavior:

```json
{
  "id": "D1",
  "kind": "patch-application",
  "summary": "Malformed unified-diff hunk counts.",
  "workaround": "Applied with --recount --unidiff-zero.",
  "scope_changed": false,
  "behavior_changed": false,
  "requirements": []
}
```

Accepted evidence may not claim changed behavior. The owner-approved
`manifest-correction` deviation is the only exception that may record
`scope_changed: true`.

## Two-commit model

```text
implementation commit
└── evidence-only commit
```

The evidence commit directly follows the implementation commit and changes only the two evidence files.

In prepare mode, those exact two generated files may be untracked regular files,
staged additions, or a mixture of the two. They are allowed only under the exact
`manifest.evidence_directory`, are excluded from implementation scope, and are
validated for byte-identical manifest content, implementation SHA, requirements,
gates, and structured deviations. A third path or a wrong evidence directory is
rejected.

Before the evidence commit:

The pack-level `evidence.json` remains pending. The completed repository copy
contains the final implementation SHA, proofs, gate results, and deviations; it
is never copied back into the pack.

```bash
python scripts/verify-agent-evidence.py prepare \
  --pack /path/to/patch-pack \
  --repo /path/to/repository \
  --implementation-commit <IMPLEMENTATION_SHA>
```

After the evidence commit:

```bash
python scripts/verify-agent-evidence.py committed \
  --pack /path/to/patch-pack \
  --repo /path/to/repository \
  --implementation-commit <IMPLEMENTATION_SHA> \
  --evidence-commit HEAD
```

Committed mode requires the evidence commit to be the direct child of the
implementation commit and to change exactly the two canonical evidence paths.
The checker verifies Git history, implementation scope, byte-identical manifest
preservation, requirement proofs, gate IDs/results, deviations, and the exact evidence-only diff. It does not rerun project tests.

After the evidence commit is pushed, the local agent waits for final-head CI and
reports its run/job/URL in external GitHub or PR metadata. It must never amend
`evidence.json` to insert that CI run or the evidence commit SHA.

Evidence created before this contract is not migrated or reconstructed. Historical files may be removed when the owner decides they are no longer useful; Git history remains the historical record.
Remote CI is a capability-dependent gate, not a universal repository requirement. Record remote CI separately from local runtime-gate evidence and apply `docs/CI_CAPABILITY_POLICY.md`.
Committed JSON evidence remains machine-verifiable; the compact final report is only a human/GPT projection. Compact reporting must not remove required fields from manifests, evidence, schemas, or helper output. Helper JSON may be captured internally, but successful JSON should not be pasted when the compact projection contains the required facts.

Gate plans, gate-run results, and evidence plans are generated separately. Use
`scripts/run-agent-gates.py` for exact-commit runtime capture and
`scripts/generate-agent-evidence.py` for proof hashes, metrics, and CI identity;
the runner never edits `evidence.json`.

Preparation follows one bounded sequence: manifest seed plus semantic evidence
plan → `scripts/prepare-agent-evidence.py` → generated manifest and resolved
plan → gate runner → evidence generator → independent verifier → compact
renderer. The preparation helper performs no CI operation; it derives scope and
resolves selectors from the exact implementation commit.

Evidence generation intentionally occurs with the new evidence directory in the
worktree. Only its declared `manifest.json` and generated `evidence.json` are
allowed. Git may report that directory as one untracked directory entry or as
individual files; the generator expands and validates directory contents rather
than trusting the directory entry. Directory-level status never permits
arbitrary files, nested directories, symlinks, or unrelated worktree changes.
Existing committed evidence remains immutable, and generated evidence must not
be manually edited after generation.
