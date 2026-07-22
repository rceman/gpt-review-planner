# Versioning

The workflow uses semantic versioning and Git tags.

- PATCH: clarification without a process contract change.
- MINOR: backward-compatible addition.
- MAJOR: changed responsibility, artifact contract, or mandatory execution order.

The active filename never changes:

```text
GPT_REVIEW_PLANNER.md
```

Projects pin both version and exact commit in `.gpt-workflow.lock`.
