# Procedure Index

This is the primary discovery entry point for the planner workflow.

```text
TASK_REQUESTED
→ INITIAL_REVIEW
→ SCOPE_PROPOSED
→ SCOPE_LOCKED
→ PATCH_PACK_READY
→ AGENT_IMPLEMENTATION
→ IMPLEMENTATION_COMPLETE
→ GPT_DELTA_REVIEW

GPT_DELTA_REVIEW
├── CORRECTION_REQUIRED
│   → GPT_CORRECTION_PATCH → AGENT_IMPLEMENTATION → IMPLEMENTATION_COMPLETE → GPT_DELTA_REVIEW
├── OWNER_DECISION_REQUIRED
│   → OWNER_DECISION → task-specific approved transition
└── MERGE_READY
    → GPT_MERGE_HANDOFF → MERGE_EXECUTION
    → MERGE_FINALIZED | MERGE_CLEANUP_BLOCKED | MERGE_BLOCKED
```

| ID | Trigger | Role | Contract | Prompt | Inputs | Terminal statuses | Next |
|---|---|---|---|---|---|---|---|
| PROC-ARCHIVE-PREP | project requested | Local agent | [archive review](PROJECT_ARCHIVE_REVIEW.md) | [prepare archive](../prompts/AGENT_PREPARE_PROJECT_ARCHIVE.md) | repository, immutable planner revision, preparation mode, task objective | ready/blocked | archive review |
| PROC-ARCHIVE-REVIEW | archive ready | GPT | [archive review](PROJECT_ARCHIVE_REVIEW.md) + [closure](REVIEW_CLOSURE_PROTOCOL.md) | [review and implement](../prompts/GPT_PROJECT_ARCHIVE_REVIEW_AND_IMPLEMENT.md), [review only](../prompts/GPT_PROJECT_ARCHIVE_REVIEW_ONLY.md) | archive, repository | review-ready/blocked | scope approval |
| PROC-INITIAL-REVIEW | task requested | GPT | [planner](../GPT_REVIEW_PLANNER.md) | project review prompt | request, repository | scope-proposed/blocked | scope lock |
| PROC-SCOPE-LOCK | owner approval | Owner/GPT | [review closure](REVIEW_CLOSURE_PROTOCOL.md) | archive review prompt | approved scope | locked/blocked | pack creation |
| PROC-PACK | scope locked | GPT | [GPT Patch Pack v2](../templates/gpt-patch-pack-v2/README.md), [compatibility authorization](COMPATIBILITY_AUTHORIZATION.md), and [handoff](PATCH_PACK_HANDOFF.md) | [create pack](../prompts/GPT_CREATE_PATCH_PACK.md) | locked scope, execution mode, and compatibility declaration | pack-ready/blocked | agent implementation |
| PROC-IMPLEMENT | pack ready | Local agent | [agent evidence](AGENT_EVIDENCE.md) | `AGENT_TASK.md` inside v2 archive | archive, SHA-256, repository, explicit mode | `IMPLEMENTATION_COMPLETE`/`CORRECTION_REQUIRED`/blocked | GPT delta review |
| PROC-DELTA | implementation complete | GPT | review closure | delta-review guidance | implementation, evidence | `CORRECTION_REQUIRED`/`OWNER_DECISION_REQUIRED`/`MERGE_READY` | correction or merge handoff |
| PROC-CORRECTION | `CORRECTION_REQUIRED` | GPT | [review closure](REVIEW_CLOSURE_PROTOCOL.md) | task-specific correction patch/handoff | verdict, defects | complete/blocked | agent implementation, then delta review |
| PROC-MERGE | `MERGE_READY` | Local agent | [cleanup contract](POST_MERGE_BRANCH_CLEANUP.md) | [merge prompt](../prompts/AGENT_FINALIZE_MERGE.md) | immutable parameters | `MERGE_FINALIZED`/`MERGE_CLEANUP_BLOCKED`/`MERGE_BLOCKED` | feature close |
| PROC-CLEANUP | merge CI success | Local agent | [post-merge cleanup](POST_MERGE_BRANCH_CLEANUP.md) | merge prompt | merge SHA, feature tip | finalized/cleanup-blocked | task close |
| PROC-RELEASE | explicit owner release task | Owner/Local agent | [release lifecycle](RELEASE_LIFECYCLE.md) and [release process](RELEASE_PROCESS.md) | [release prompt](../prompts/AGENT_RELEASE_VERSION.md) | exact lifecycle mode, target version, authorization | source-checked/prepared/release-ready/tag-ready/finalized/blocked | separate release close |
| PROC-CI-POLICY | any CI decision | GPT/Owner | [CI capability policy](CI_CAPABILITY_POLICY.md) | [CI helper](../scripts/check-github-ci.py) | policy, SHA | success/pending/unavailable/blocked | current procedure |
| PROC-RUNTIME-UPGRADE | authorized runtime upgrade | Local agent | [runtime upgrade](RUNTIME_UPGRADE_POLICY.md), [migration](PERSISTED_STATE_MIGRATION_POLICY.md) | [runtime upgrade](../prompts/AGENT_RUNTIME_UPGRADE.md) | task declaration, source/target identity, state scope | succeeded/failed/rollback | verification or incident |
| PROC-INCIDENT | incident trigger or unknown readiness failure | Local agent/GPT | [incident response](INCIDENT_RESPONSE_POLICY.md) | [incident diagnosis](../prompts/AGENT_INCIDENT_DIAGNOSIS.md), [recovery](../prompts/AGENT_RUNTIME_RECOVERY.md) | logs, phase, process/state identity | diagnosed/checkpointed/blocked | durable plan update |
| PROC-STATE-MIGRATION | authorized persisted-state change | Local agent | [migration policy](PERSISTED_STATE_MIGRATION_POLICY.md) | [migration](../prompts/AGENT_PERSISTED_STATE_MIGRATION.md), [reconciliation](../prompts/AGENT_STATE_RECONCILIATION.md) | old/new schema, authorization, backup | migrated/rolled-back/blocked | target validation |
| PROC-DIRECT-SESSION | bounded status/continue request | Local agent | [direct session policy](DIRECT_AGENT_SESSION_CONTROL_POLICY.md) | [session implementation](../prompts/AGENT_DIRECT_SESSION_CONTROL_IMPLEMENTATION.md) | registered project/session, bounded payload | delivered/rejected | current authorized operation |
| PROC-TOOL-AUDIT | protocol/tool release gate | Local agent/GPT | [tool integrity](TOOL_CONTRACT_INTEGRITY_POLICY.md) | [tool audit](../prompts/AGENT_TOOL_CONTRACT_AUDIT.md) | live tools/list, handlers, schemas | parity/failed | release checkpoint |
| PROC-CHAT-HANDOFF | conversation transition | GPT/local agent | [handoff checkpoint](CHAT_HANDOFF_CHECKPOINT.md) | [chat handoff](../prompts/AGENT_CHAT_HANDOFF.md) | exact refs, runtime state, plan, next action | frozen/blocked | next conversation |

Ownership is explicit: GPT owns architecture, principal implementation, tests, correction patches, and delta review. The local agent owns integration, runtime gates, evidence, merge execution, and cleanup. `IMPLEMENTATION_COMPLETE` returns control to GPT. `CORRECTION_REQUIRED` requires a GPT-authored correction handoff or patch and returns through implementation to delta review; it does not automatically lead to merge. `OWNER_DECISION_REQUIRED` waits for the owner and follows only a task-specific approved transition. `MERGE_READY` requires GPT to provide `GPT_MERGE_HANDOFF`; it does not mean merge execution is complete. `MERGE_FINALIZED` closes the current feature task. Backlog work and release work start only as separate tasks, with release requiring explicit owner instruction.

Load the linked normative contract and reusable prompt before execution; this index is a map, not a replacement for them.

Release work has exactly two modes, `implementation_unreleased` and
`release_publication`; load [`RELEASE_LIFECYCLE.md`](RELEASE_LIFECYCLE.md) and
run the matching state gate before `MERGE_READY`. A source implementation may
not be presented as a publication or tag-ready release.
