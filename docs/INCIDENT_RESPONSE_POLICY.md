# Incident Response Policy

Enter incident mode after any of these triggers: two failed activation attempts; 15 minutes without forward progress during cutover; installed/running mismatch; readiness failure with unknown primary cause; rollback failure; an inconsistent task/run/plan/project graph; or repeated discovery of one blocker per activation.

Incident mode permits bounded logs, status, source inspection, persisted-state inspection, process identity inspection, hypothesis testing, and read-only diagnostics. Until the exact root cause is established, it prohibits another restart, another install, another migration, bypass chains, unrelated feature work, and blind retry.

The incident record MUST contain the exact first fatal line, startup phase, competing hypotheses, source/log/state correlation, observed impact, and a corrective-action checkpoint. Feature work resumes only after that checkpoint and a durable plan update record the accepted correction and next action.

Readiness timeout alone is not a diagnosis: record the startup phase and primary fatal line or state that the cause remains unknown and keep the incident open.
