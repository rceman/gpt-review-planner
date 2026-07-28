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
→ CORRECTION_REQUIRED | OWNER_DECISION_REQUIRED | MERGE_READY
→ MERGE_EXECUTION
→ MERGE_FINALIZED | MERGE_CLEANUP_BLOCKED
→ OPTIONAL_SEPARATE_RELEASE_TASK
```

| ID | Trigger | Role | Contract | Prompt | Inputs | Terminal statuses | Next |
|---|---|---|---|---|---|---|---|
| PROC-ARCHIVE-PREP | project requested | GPT | [archive preparation](../docs/PATCH_PACK_HANDOFF.md) | archive workflow guidance | repository, target | ready/blocked | initial review |
| PROC-ARCHIVE-REVIEW | archive ready | GPT | [review closure](REVIEW_CLOSURE_PROTOCOL.md) | archive review prompt | archive, scope | review-ready/blocked | scope approval |
| PROC-INITIAL-REVIEW | task requested | GPT | [planner](../GPT_REVIEW_PLANNER.md) | project review prompt | request, repository | scope-proposed/blocked | scope lock |
| PROC-SCOPE-LOCK | owner approval | Owner/GPT | [handoff](PATCH_PACK_HANDOFF.md) | patch-pack prompt | approved scope | locked/blocked | pack creation |
| PROC-PACK | scope locked | GPT | [patch-pack format](PATCH_PACK_FORMAT.md) | [create pack](../prompts/GPT_CREATE_PATCH_PACK.md) | locked scope | pack-ready/blocked | agent implementation |
| PROC-IMPLEMENT | pack ready | Local agent | [agent evidence](AGENT_EVIDENCE.md) | pack handoff | pack, inputs | `IMPLEMENTATION_COMPLETE`/blocked | GPT delta review |
| PROC-DELTA | implementation complete | GPT | review closure | delta-review guidance | implementation, evidence | `CORRECTION_REQUIRED`/`OWNER_DECISION_REQUIRED`/`MERGE_READY` | correction or merge handoff |
| PROC-CORRECTION | correction required | GPT | bounded correction contract | correction handoff | verdict, defects | complete/blocked | delta review |
| PROC-MERGE | `MERGE_READY` | Local agent | [cleanup contract](POST_MERGE_BRANCH_CLEANUP.md) | [merge prompt](../prompts/AGENT_FINALIZE_MERGE.md) | immutable parameters | `MERGE_FINALIZED`/`MERGE_CLEANUP_BLOCKED`/`MERGE_BLOCKED` | feature close |
| PROC-CLEANUP | merge CI success | Local agent | [post-merge cleanup](POST_MERGE_BRANCH_CLEANUP.md) | merge prompt | merge SHA, feature tip | finalized/cleanup-blocked | task close |
| PROC-RELEASE | explicit owner release task | Owner/Local agent | [release process](RELEASE_PROCESS.md) | [release prompt](../prompts/AGENT_RELEASE_VERSION.md) | version, authorization | prepared/finalized/blocked | separate release close |
| PROC-CI-POLICY | any CI decision | GPT/Owner | [CI capability policy](CI_CAPABILITY_POLICY.md) | [CI helper](../scripts/check-github-ci.py) | policy, SHA | success/pending/unavailable/blocked | current procedure |

Ownership is explicit: GPT owns architecture, principal implementation, tests, correction patches, and delta review. The local agent owns integration, runtime gates, evidence, merge execution, and cleanup. `IMPLEMENTATION_COMPLETE` returns control to GPT. `CORRECTION_REQUIRED` requires a GPT-authored correction handoff or patch. `MERGE_READY` requires GPT to provide the next merge handoff; it does not mean merge execution is complete. `MERGE_FINALIZED` closes the current feature task. Backlog work and release work start only as separate tasks, with release requiring explicit owner instruction.

Load the linked normative contract and reusable prompt before execution; this index is a map, not a replacement for them.
