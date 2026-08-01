# Persisted-State Migration Policy

Every persisted schema change MUST declare the old and new schema/version, exact record scope, compatibility authorization, direction, dry-run behavior, backup, canonical migration operation, target-decoder validation, atomic commit, rollback, and removal condition for migration tooling.

Migration is one-time and bounded. Permanent dual readers, fallback field aliases, target activation before required migration, ad hoc field deletion when a canonical migration exists, and fake placeholder records are forbidden. Migration tooling is removed when its declared removal condition is met.

Immutable historical records remain historical and may retain their historical status. Current operational pointers MUST NOT reference history-only records. Current operational pointers are distinct from immutable history. Migration clears obsolete operational references without fabricating completion. A current plan pointer must reference a valid canonical current plan; a project is not operationally active until its required initial plan exists.

The migration transaction is `backup → dry-run → canonical apply → target decode → atomic commit → verification`, with rollback proof for every changed record. Compatibility is `scope=none` unless an owner explicitly authorizes a complete bounded declaration.
