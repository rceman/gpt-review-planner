# Durable project identifiers

Each adopted project has one strict `project-identifiers.json` allocation
record. It binds the canonical gateway `project_id` to an immutable three-letter
uppercase `project_code` and the next task and ADR counters. The planner and
gateway fixtures demonstrate the assignments `GRP` and `GTW`.

Validate a record with:

```bash
python3 scripts/validate-project-identifiers.py project-identifiers.json
```

## Allocation rules

Allocation is an atomic read-lock-validate-increment-write transaction over the
record. Allocators do not scan history, compute a maximum, or infer the next
number from filenames. A number is never reused, including after a failed or
abandoned task. The record's project code is immutable after adoption.

Canonical identifiers are:

```text
task:   <CODE>-T<N>
run:    <TASK-ID>-R<N>
ADR:    <CODE>-A<N>
branch: task/<TASK-ID>-<slug>
```

Numeric parts start at one, have no leading zero, and run numbering is local to
its task. A task revision or replacement receives a new identifier and branch;
the durable record must state `replaces` or `supersedes` when that relationship
is needed. Existing identifiers are not renamed or aliased.

## UUID history cutover

Already persisted UUID history remains readable as long as that history exists.
That historical reader is read-only and is not a new operational identifier
path. It does not authorize UUID creation, mutation aliases, fuzzy lookup, or
dual operational paths. Historical UUID records remain immutable; new
operational identifiers use the adopted project code and canonical syntax.
