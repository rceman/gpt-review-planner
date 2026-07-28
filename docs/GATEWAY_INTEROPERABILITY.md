# GPT GitHub Gateway Interoperability

`gpt-review-planner` owns executable patch-pack semantics. `gpt-github-gateway` owns protocol-v2 transport and local execution materialization. `rceman/typer` is a passive Git bus.

| Artifact or responsibility | Owner |
|---|---|
| `manifest.json` | `gpt-review-planner` |
| `evidence.json` | `gpt-review-planner` |
| `AGENT_HANDOFF.md` | `gpt-review-planner` |
| `patch_pack_scope.py` | `gpt-review-planner` |
| `verify-agent-evidence.py` | `gpt-review-planner` |
| validator JSON result schema | `gpt-review-planner` |
| `TASK_REQUEST.json` | `gpt-github-gateway` |
| `*.taskbundle.json` | `gpt-github-gateway` |
| `*.result.json` | `gpt-github-gateway` |
| safe archive extraction | `gpt-github-gateway` |
| Airelay routing | `gpt-github-gateway` |
| `rceman/typer` directory layout | `gpt-github-gateway` |

Gateway protocol v2 submits one deterministic base64 `tar.gz` payload in one JSON file and publishes one final atomic result. The gateway resolves `manifest.workflow.commit`, invokes `scripts/validate-patch-pack.py --format json`, safely materializes the pack, and asks the local agent to read the canonical `AGENT_HANDOFF.md`.

The planner does not implement task-bundle base64 transport, bus paths, gateway IDs, execution modes, Airelay session management, or result publication. Transport-only fields such as `gateway_id`, `project_id`, `task_id`, execution mode, archive digest, encoded content, result path, and session identity are forbidden in the planner manifest.

Delivery modes are separate from transport implementation:

- `manual-download`: validates archive/sidecar naming and the Downloads handoff sentence;
- `gateway-task-bundle`: validates the same semantic pack and a transport-neutral materialized-pack handoff;
- `prompt-only` and `no-action`: validate response contracts without claiming a pack.

Protocol-v1 records remain gateway read compatibility and do not alter planner pack semantics.
