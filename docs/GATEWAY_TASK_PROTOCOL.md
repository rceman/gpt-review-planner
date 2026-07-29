# Gateway Task Protocol

## Durable plan before execution

Every GPT-originated executable gateway task has a non-executable plan committed first to the same `rceman/typer` project branch:

```text
inbox/<task_id>.plan.json
```

The later `inbox/<task_id>.taskbundle.json` commit must descend from the plan commit and reference both the plan path and commit. The plan record is ignored by executable discovery and contains task identity, repository/default branch, exact base revision, objective, declared file operations, acceptance criteria, gates, constraints, role boundary, dependencies, current blocker, and next transition. This record is the continuation source for another ChatGPT conversation.

## Responsibility boundary

GPT inspects repository state and authors the behavior contract, fixtures, production changes, tests, schemas, docs, and executable patch pack. The local agent applies the supplied pack, restores dependencies, runs runtime gates, creates evidence/commits, and performs only narrow repairs demonstrated by actual failures. The agent does not redesign from prose.

## Single agent-authored result

The only agent-authored terminal artifact is `agent-result.json`, validated by `schemas/gateway-agent-result-v2.schema.json` and `scripts/validate-gateway-agent-result.py`.

The gateway appends two authoritative runtime values to the handoff:

- result JSON path;
- executable `complete-task` command path.

The agent writes the JSON and invokes the command for every terminal status:

- `succeeded`;
- `needs_gpt_revision`;
- `failed`.

Interactive Airelay/Codex text is an execution log only. It does not complete the task and is not copied into a separate Markdown result.

## Finalizer responsibilities

The gateway-owned finalizer validates task identity, strict JSON, status contract, manifest gate coverage, commit ancestry, exact branch/remote state, worktree cleanliness, patch scope, and committed evidence. It then publishes one authoritative bus result plus checkpoint update in one project-branch commit, clears `active_task_id`, and advances the queue. The agent must not reproduce these checks as a hand-written shell block.

For non-success statuses, commits are optional but a bounded summary is mandatory. `needs_gpt_revision` also requires `next_action`.

## Missing finalization

When the agent session becomes promptable/free without a finalized result, the gateway issues one bounded corrective prompt instructing the agent to write `agent-result.json` and run `complete-task`. If it still does not finalize, the gateway publishes a synthetic `failed` result and clears project activity.

## Compatibility

A deployed gateway predating this protocol may temporarily require both `agent-result.json` and `AGENT_RESPONSE.md`. That compatibility path is bootstrap-only. Newly generated planner packs use the JSON-only protocol once the matching gateway implementation is installed.
