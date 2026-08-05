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
