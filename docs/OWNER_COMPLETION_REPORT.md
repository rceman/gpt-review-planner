# Owner Completion Report

This is the sole normative authority for the human-first GPT-to-owner
completion report. `completion.json`, gateway run reports, CI JSON, evidence manifests,
and terminal logs remain machine or execution evidence; none of those records
is the owner-facing report.

## Successful report order

Every successful owner report MUST use this order:

1. One-line outcome in plain language.
2. `What changed`.
3. `Why it matters`.
4. `Availability`, stating what is usable now and what remains unavailable.
5. `Next action`, containing one exact decision or authorization, or exactly
   `None — no owner action required`.
6. `Technical record`, last and compact.

The report must describe only states directly established by the evidence. A
successful result is not permission to infer a later state.

## Canonical states

Use exactly these state words when they apply: `implemented`, `reviewed`,
`merged`, `released`, `installed`, `running`, `activated`, and `blocked`.
Never replace them with `done` or `complete everywhere`. `merged`, `released`,
`installed`, `running`, and `activated` are independent states. A source merge is never runtime availability.

`Availability` MUST name the usable state and every relevant unavailable or
unproven later state. In particular, released does not prove installed,
installed does not prove running, and running does not prove activated or
connector refresh.

## Tool changes

When tool changes apply, use exactly these groups and one plain-language line
per changed tool:

### New tools

- `<tool>`: `<plain-language behavior/impact>`
- `None` when the group is empty.

### Updated tools

- `<tool>`: `<plain-language behavior/impact>`
- `None` when the group is empty.

### Removed tools

- `<tool>`: `<plain-language behavior/impact>`
- `None` when the group is empty.

Bare comma-separated endpoint lists are not a report. The per-tool line is
required even when the behavior is unchanged apart from the stated update.

## Blocked and failed reports

Failures and blocks use a separate projection, in this order:

1. One-line `BLOCKED` outcome.
2. `Owner impact`.
3. `Required decision`.
4. `Preserved state`.
5. `Technical record`, last.

Do not bury the blocker after logs or a long gate inventory. Use `blocked` as
the state and do not imply implementation, merge, release, installation,
running, or activation unless that state was independently established.

## Prose and technical record boundary

Primary owner prose excludes raw hub revisions, local paths, PIDs, exhaustive
gate inventories, repeated SHAs, and unchanged-state dumps unless one is
material to the decision or incident. The final `Technical record` may contain
the final or accepted SHA, relevant CI status and ID, a durable compact task or
run ID when useful, deviations, and prohibited-operation confirmation.

After cutover, use compact IDs. Include historical UUIDs only when audit
continuity requires them. The report is written in the owner's conversation
language; local-agent execution communication remains governed by
`docs/AGENT_COMMUNICATION_LANGUAGE.md`.

This planner slice does not install or claim a versioned GPT Tunnel Operator Guide,
`session_start`, or `session_sync` enforcement. Those are later gateway integration work. Manual handoffs are the interim enforcement boundary.

## Technical record

The technical record is always last in the owner projection. Keep machine
evidence in its canonical records and refer to it rather than pasting raw JSON,
logs, or duplicated fields into the owner report.
