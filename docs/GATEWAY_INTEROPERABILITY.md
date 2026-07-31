# GPT GitHub Gateway Interoperability

`gpt-review-planner` owns executable patch-pack semantics. `gpt-github-gateway` owns protocol-v2 transport and local execution materialization. `rceman/typer` is a passive Git bus.

| Artifact or responsibility | Owner |
|---|---|
| `manifest.json` | `gpt-review-planner` |
| `evidence.json` | `gpt-review-planner`, repository-evidence mode only |
| `completion.json` | gateway-managed task, planner schema and validator |
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

Before `gateway-task-bundle` submission, GPT commits
`inbox/<task_id>.plan.json` to the same project branch. The executable bundle
commit must descend from and reference that plan commit. The plan is passive
continuity state and is not discovered as executable input.

Planner-owned terminal semantics are:

- one strict agent-authored `completion.json` in `gpt_tunnel_managed` mode;
- statuses `succeeded`, `needs_gpt_revision`, and `failed`;
- mandatory finalization through the gateway's finalize command;
- no interactive owner dialogue from a gateway execution turn;
- a required `TERMINAL_OUTPUT_PROTOCOL` handoff section.

Gateway-owned mechanics are:

- generating the finalizer and authoritative paths;
- validating repository, commits, branch, scope, gates, and evidence;
- enriching and atomically committing the bus result and checkpoint;
- clearing project activity and advancing the queue;
- corrective reprompt and synthetic terminal failure.

See [`GATEWAY_TASK_PROTOCOL.md`](GATEWAY_TASK_PROTOCOL.md).

Historical protocol-v1 records remain immutable history and are not read as a
workflow 2.0.0 tunnel completion.
