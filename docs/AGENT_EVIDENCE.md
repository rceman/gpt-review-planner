# Committed Agent Evidence

GPT Patch Pack v1 retains separate implementation and evidence commits.

The evidence directory is declared by the pack and contains exactly
`manifest.json` and `evidence.json`. The manifest is copied byte-for-byte from
the pack.

Evidence must include requirement proofs, ordered passing gates, deviations,
and:

```json
{
  "compatibility_scope": "none",
  "compatibility_authorized": false,
  "compatibility_features_added": [],
  "legacy_paths_added": [],
  "fallbacks_added": [],
  "migration_behavior_added": []
}
```

Without explicit authorization every compatibility array is empty. A gate
failure that appears to require compatibility must produce
`BLOCKED_UNAUTHORIZED_COMPATIBILITY_CHANGE`, not a shim or deviation.

Use `generate-agent-evidence.py`, then verify before and after the evidence-only
commit with `verify-agent-evidence.py`. The evidence commit directly follows the
implementation commit and changes exactly the two evidence files.

A missing required runner is an environment failure, never a passing gate. Do
not record `status: pass` while stating that a required tool was unavailable;
restore the prerequisite or stop before creating committed evidence.
