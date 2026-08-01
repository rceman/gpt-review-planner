# Agent Prompt: Incident Diagnosis

Own exact root-cause discovery; do not wait for GPT to enumerate shell commands. Load `docs/INCIDENT_RESPONSE_POLICY.md`.

Collect bounded evidence: exact first fatal line, startup phase, installed/running versions, process identities, persisted-state records, authoritative refs, and protocol/tool output. State competing hypotheses and test them with read-only source, log, and state correlation. Do not perform another restart, installation, migration, blind retry, bypass, or unrelated feature change while the cause is unknown.

End with an incident report and a corrective-action checkpoint. If the durable plan changes, update it through the canonical workflow-v2 CLI and record the new authoritative revision before feature work resumes.
