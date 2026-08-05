# Airelay managed upgrade contract

This document defines the planner-side contract for an externally supervised
Airelay rolling upgrade. It is a declaration and evidence boundary; the
planner does not install binaries, stop or start processes, send signals, or
mutate gateway state.

## Inputs and authority

The session launch recipe is the only imported launch identity. It contains
the absolute working directory, the executable invocation path and its
resolved path, exact executable and controller versions, the child invocation
path and its resolved path, child argv, a separate Codex resume UUID, approved
flags, and environment references. A shell command string, secret value,
relative path, duplicate argv item, session key substituted for the resume
UUID, or unapproved flag is forbidden.
The controller protocol version is a positive safe JSON integer, independently
validated from the SemVer runtime version.
recipe_sha256 is the SHA-256 of the canonical sorted JSON recipe after
removing the recipe_sha256 field itself.

Invocation and resolved paths are separate proofs. The external supervisor
executes the invocation path pinned by a versioned release recipe and verifies
the resolved target and build digest before stopping the old controller. A
mutable global symlink alone is not sufficient authority; the resolved target
must be recorded and checked.

An upgrade request names the exact target release path and build digest,
ordered selected sessions, expected current identities, graceful timeout, and
separate install, restart, and force-stop authorizations. There is no implicit
all-sessions selection. If airelay_master is selected, it is last. A
force_stop_policy of owner_authorized requires a separately authorized
force-stop operation; never requires that authorization to be absent.
Authorization is explicit: true requires a non-empty source, while false may
omit the source or use null.

## Transaction and proof order

The supervising implementation must prove:

~~~text
inspect -> prepare -> backup -> migrate -> validate -> drain -> stop -> start
-> readiness -> verify -> complete
~~~

Target persisted state and its decoder are validated before old-runtime
shutdown. Graceful timeout is followed by force-stop only when separately
authorized. Prompts are rejected during the declared rollout window.
Readiness must prove the exact new recipe, version, PID, controller protocol,
working directory, resume identity, and ready status.

Every session receipt includes the old identity and state-specific new,
readiness, failure, and rollback proofs. A successful aggregate requires every
selected session to be ready. A rollback restores the exact old identity and
must not be represented as partial success. Immutable historical records are
not rewritten to manufacture current operational state.

## Ownership and scope

The planner validates the machine-readable recipe, request, receipt, schema
parity, ordering, identity proofs, and authorizations. The external operator
owns installation, process control, persistence migration, health checks, and
rollback execution. Any real upgrade requires a separately authorized
operational task with a complete backup and rollback record.
