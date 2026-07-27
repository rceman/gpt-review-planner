# Bounded Review and Closure Protocol

## Purpose

This protocol prevents an approved implementation from entering an unbounded
cycle in which every correction triggers another unconstrained full review and
newly invented hardening requirements become merge blockers.

The protocol does not suppress legitimate defects. It separates discovery from
merge blocking, locks the approved acceptance contract, verifies corrections by
delta, and defines an explicit stopping condition.

## Core terms

- **Acceptance contract** — the owner-approved set of stable acceptance criteria
  for the current patch scope.
- **Scope lock** — the approved objective, finding IDs, file operations,
  exclusions, and acceptance criteria. Approval creates the lock.
- **Initial full review** — the first independent review of the relevant project
  surface before implementation.
- **Delta review** — review limited to approved findings, changed surfaces,
  acceptance criteria, required gates, and demonstrable regressions.
- **Merge blocker** — a finding that meets the blocker threshold below.
- **Follow-up backlog** — valuable work that does not prevent safe acceptance of
  the approved patch.
- **Observation** — context or an idea that requires no action in the current
  task.

## Acceptance contract

Before implementation, every mandatory outcome MUST have a stable acceptance
criterion ID such as `AC-001`. Each criterion states:

```yaml
id: AC-001
statement: The approved behavior is implemented.
severity_if_failed: blocker
verification: static | test | ci | owner
source: owner | spec | adr | workflow
```

The approved patch scope MUST identify the acceptance criteria, covered finding
IDs, exact file operations, exclusions, runtime gates, and owner decisions.
Silence or partial approval does not create a scope lock.

After approval, a reviewer MUST NOT strengthen the acceptance contract and then
classify the new stronger requirement as a blocker. A contract change requires
explicit owner approval or a qualifying reopen condition.

## Blocker threshold

A finding may enter `MERGE_BLOCKERS` only when at least one blocking basis is
supported by concrete evidence:

1. an approved acceptance criterion fails;
2. a correction introduces a demonstrable regression;
3. a critical or high-severity pre-existing defect was missed and materially
   prevents safe use;
4. a security vulnerability is confirmed;
5. data loss or corruption is credible;
6. a public or persisted compatibility contract is broken;
7. a required quality gate fails;
8. the feature is materially unusable for its approved objective.

The finding MUST name its blocking basis and the violated acceptance criterion
when applicable.

The following are non-blocking unless the owner explicitly promotes them into
scope:

- additional hardening;
- documentation completeness beyond the approved criterion;
- maintainability improvements;
- optional test expansion;
- future architecture;
- style preferences;
- a newly proposed stronger provenance or validation contract.

## Review modes

### Initial review

The initial review is full within the effective owner-selected scope. It may
surface independent critical defects and produces stable findings plus the exact
proposed patch scope.

### Post-implementation review

After implementation or the first correction, the normal mode is `delta`.
The reviewer checks only:

- closure of approved finding IDs;
- approved acceptance criteria;
- files and contracts changed by the patch;
- required runtime and CI evidence;
- regressions caused by those changes.

The reviewer MUST NOT restart an unconstrained full review merely because the
repository is available again.

A full reopen is allowed only for:

- an explicit owner request;
- a material architecture change outside the approved design;
- new concrete evidence of a critical or high-severity defect.

The reopen reason MUST be recorded.

## Finding lifecycle

Every finding has a stable ID and one state:

```text
open
in_progress
verified_closed
deferred
superseded
```

A closed finding may be reopened only with new evidence, a concrete regression,
or a written explanation of why the previous closure was invalid. Rephrasing a
closed finding as a stronger preference is not a valid reopen.

## Correction-round budget

The normal workflow permits one correction round after the first implementation.
A further correction round requires a demonstrable regression, a still-failing
approved acceptance criterion, or a newly evidenced critical/high-severity
blocker. Low- and medium-severity improvements move to a separate task.

This is a governance limit, not permission to accept a known security or data
integrity defect.

## Required queues and verdicts

Every implementation-result review separates findings into exactly these
queues:

```text
MERGE_BLOCKERS
FOLLOW_UP_BACKLOG
OBSERVATIONS
```

The closure verdict is one of:

```text
CORRECTION_REQUIRED
OWNER_DECISION_REQUIRED
MERGE_READY
```

`MERGE_READY` is mandatory when all of the following are true:

- every approved acceptance criterion passes;
- all required agent-executed gates and exact-SHA CI pass;
- no evidenced merge blocker remains;
- declared scope and actual diff agree;
- unresolved items are only follow-up work or observations.

After declaring `MERGE_READY`, the reviewer MUST stop the current review. It may
record follow-up tasks but MUST NOT continue searching for optional improvements
inside the same closure cycle.

## Diminishing-return stop rule

The reviewer stops expanding the current patch when additional changes are
predominantly hardening, completeness, or future design; when those changes are
not required by the approved acceptance contract; or when further modification
would introduce more integration risk than the evidenced benefit.

Validators, schemas, policy documents, and test matrices are inherently
open-ended. “Can be made stricter” is not a completion criterion.

## Output contract

An implementation-result review records:

```yaml
review_mode: delta | full-reopen
scope_lock: <stable identifier or approved scope reference>
correction_round: <integer>
closed_findings: []
reopened_findings: []
merge_blockers: []
follow_up_backlog: []
observations: []
closure_verdict: MERGE_READY | CORRECTION_REQUIRED | OWNER_DECISION_REQUIRED
```

Each blocker includes evidence, blocking basis, affected acceptance criteria,
impact, and the minimum correction required.

## Local-agent boundary

The local coding agent applies the approved patch, runs required gates, fixes
verified narrow integration defects, and records evidence. The agent MUST NOT
promote optional improvements into implementation scope. Any material scope or
behavior change requires owner approval.
