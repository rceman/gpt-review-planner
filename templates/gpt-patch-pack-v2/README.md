# GPT Patch Pack v2

GPT Patch Pack v2 is the only new-task executable pack format. It is a data-only
archive containing `MANIFEST.json`, `SHA256SUMS`, `AGENT_TASK.md`, and
`payload/changes.patch`. The v2 runner performs the fixed Git apply operations;
archive members are never executed.

Every pack declares exactly one `execution_mode`: `gpt_tunnel_managed` or
`repository_evidence`. Tunnel mode has one `completion.json` and one gateway
report authority and forbids repository evidence. Repository mode has one
repository evidence authority.

Use `scripts/build-gpt-patch-pack-v2.py`, `scripts/validate-patch-pack-v2.py`,
and `scripts/gpt-patch-pack-runner-v2.py`. Historical v1 artifacts remain
history only and are not creation, negotiation, or fallback paths.
