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

Gate commands and expectations live only in `manifest.json`. `evidence.json` records compact results by gate ID:

```json
{"id":"unit","status":"pass","exit":0,"tests":47,"summary":"Ran 47 tests ... OK"}
```

GitHub Actions gates use run/job IDs and a URL. The checker requires every manifest gate exactly once and rejects failed or skipped required gates.

## Deviations

Deviations are embedded in `evidence.json`; there is no separate Markdown deviation report. The presence of an entry means it is documented:

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

Accepted evidence may not claim changed scope or changed behavior.

## Two-commit model

```text
implementation commit
└── evidence-only commit
```

The evidence commit directly follows the implementation commit and changes only the two evidence files.

Before the evidence commit:

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

The checker verifies Git history, implementation scope, byte-identical manifest preservation, requirement proofs, gate IDs/results, deviations, and the exact evidence-only diff. It does not rerun project tests.

Evidence created before this contract is not migrated or reconstructed. Historical files may be removed when the owner decides they are no longer useful; Git history remains the historical record.
