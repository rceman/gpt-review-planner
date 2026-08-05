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
task:   <CODE>-TSK<N>
run:    <TASK-ID>-RUN<N>
ADR:    <CODE>-ADR<N>
branch: task/<TASK-ID>-<slug>
```

Numeric parts start at one, have no leading zero, and run numbering is local to
its task. A task revision or replacement receives a new identifier and branch;
the durable record must state `replaces` or `supersedes` when that relationship
is needed. Existing identifiers are not renamed or aliased.

## UUID history cutover

Already persisted UUID history remains readable as long as that history exists.
That historical reader is read-only and is not a new operational identifier
path. Persisted pre-activation single-letter-token records are likewise
immutable read-only history only; they are not canonical new operational
syntax. Neither history class authorizes UUID creation, mutation aliases,
fuzzy lookup, or dual operational paths. New operational identifiers use the
adopted project code and canonical `TSK`/`RUN`/`ADR` syntax.
