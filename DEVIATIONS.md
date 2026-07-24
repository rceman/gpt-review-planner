# Agent Deviations

Status: documented

## DEV-001 — Malformed patch hunk counts

The supplied `patch/changes.patch` failed:

```text
git apply --check patch/changes.patch
corrupt patch at line 17
```

The local coding agent applied the same payload using:

```text
git apply --check --recount --unidiff-zero patch/changes.patch
git apply --index --recount --unidiff-zero patch/changes.patch
```

Impact:

- no path was added outside the declared implementation scope;
- no intended file content changed;
- no behavior contract or acceptance criterion changed;
- the implementation commit still contains exactly the five declared files.

This patch-application workaround is a documented deviation.
