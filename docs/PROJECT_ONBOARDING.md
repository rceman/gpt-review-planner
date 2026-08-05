# Project onboarding contract

Project onboarding is a planner-owned, journaled transaction for registering a
repository and its initial operational records. It does not install software,
invoke a runtime, mutate a project checkout, or authorize implementation work.

The machine-readable contract is defined by:

- [`schemas/project-onboarding-request.schema.json`](../schemas/project-onboarding-request.schema.json)
- [`schemas/project-onboarding-receipt.schema.json`](../schemas/project-onboarding-receipt.schema.json)
- [`scripts/validate-project-onboarding.py`](../scripts/validate-project-onboarding.py)

Validate the canonical Airelay examples with:

```bash
python3 scripts/validate-project-onboarding.py \
  --request fixtures/project-onboarding/airelay-request.json
python3 scripts/validate-project-onboarding.py \
  --receipt fixtures/project-onboarding/airelay-activated-receipt.json
```

## Transaction and authority

The durable phases are `prepared → hub_committed → activated`. A failed phase
enters `recovery_required` and may finish as `rolled_back`; a receipt must
prove the state-dependent records, hashes, timestamps, and recovery status.
The receipt is a proof record, not a second project registry. Registration and
declaration are separate from implementation, installation, invocation,
release, and merge authority.

The request binds a project ID to an absolute repository root, an exact remote
and URL, a default branch, an optional workflow pin, and a schema-v2 idle
initial plan. The plan's project ID must match the request; it must not invent
an active task or run. Airelay session use is explicit: the canonical fixture
requires the registered `airelay_master` session.

Onboarding records the hub revision before and after the operation and the
exact changed paths. Filesystem, Git, and runtime operations are not one
cross-system atomic transaction; recovery is instead driven by the durable
journal and immutable digests. Historical records remain historical, while
current operational pointers must reference valid current records.

Unknown fields, duplicate JSON keys, unsafe paths, invalid identifiers, bad
SHA values, malformed timestamps, invalid plan versions, and state/proof
contradictions are rejected by the standard-library validator. There is no
manual-config fallback and no gateway implementation in this O1 planner slice.

## Required identity and recovery proof

Every managed project selects a globally unique three-letter `project_code`.
The request also declares `gateway_state_dir`; the activated mirror must be
exactly `<gateway_state_dir>/git-mirrors/<project_id>.git`. Repository values
must be normalized absolute paths or Git URLs containing `:`. Airelay session
keys use the gateway-compatible alphanumeric/dot/underscore/hyphen syntax.

Session proof is binary after preflight: a required session is `active` and
contains its key; an optional session is `not_required` and contains neither a
key nor a controller protocol version. `unverified` is not a receipt state.

The receipt records distinct managed-registry before/after digests plus the
project, plan, and identifiers record digests. Hub proof contains exactly the
three canonical project, current-plan, and identifiers paths. Recovery receipts
name their `last_completed_state` and retain the proof for that state. A
`rolled_back` receipt additionally contains a rollback proof whose managed
digest equals the original managed-before digest; rollback from a committed
hub state includes the hub rollback revision and exact path set. All timestamps
are chronological, and recovery and receipt rollback timestamps are identical.
Every prepared-or-later receipt proves `worktree_proof.clean: true`, an active
session includes its positive controller protocol version, and an optional
session is explicitly `not_required`. Repository branch and default branch,
created-project repository identity, and mirror repository identity must match
the repository proof exactly. Committed hub revisions and all phase timestamps
are strictly increasing; `updated_at` may equal, but never precede, the latest
phase.
