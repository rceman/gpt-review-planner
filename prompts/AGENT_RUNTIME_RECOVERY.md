# Agent Prompt: Runtime Recovery

Use this prompt only for bounded recovery of a stopped or inconsistent runtime. Load `docs/RUNTIME_UPGRADE_POLICY.md` and `docs/INCIDENT_RESPONSE_POLICY.md` first.

Inspect installed versus running version, stale PIDs, executable inode identity, port ownership, startup phase, persisted state, and the exact first fatal line. A healthy tunnel with a stopped gateway, a replaced installed inode, or a version mismatch is evidence to correlate, not permission to retry.

After an incident trigger, do not restart, reinstall, migrate again, or use a bypass chain until the root cause and corrective checkpoint are recorded. Use bounded foreground diagnostics, preserve logs, verify process identity, and record rollback state. Resume feature work only after the durable plan is updated with the incident closure and exact next action.
