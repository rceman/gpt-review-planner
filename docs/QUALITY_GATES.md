# Quality gates declaration

`quality-gates.json` is a repository-relative, dependency-free declaration for
the later deterministic prepare, merge, and release runners. This slice defines
the contract and validator only; it does not execute commands, clean files,
write generated outputs, or adopt a root declaration.

Validate a declaration with:

```bash
python3 scripts/validate-quality-gates.py quality-gates.json
```

The canonical template is
[`templates/project/quality-gates.json`](../templates/project/quality-gates.json).
Its top-level fields are exactly `schema_version`,
`unmatched_changed_path`, `cleanup`, `generated`, `rules`, and `release`.

## Selection and ordering

Changed paths are matched against `rules` in declaration order. A changed path
that matches no rule is rejected; there is no implicit catch-all rule. Selected
prepare or merge commands retain declaration order. Command IDs are globally
unique across all rule phases and release commands; a future runner must
de-duplicate selected IDs before execution. File arguments are sorted and unique
before they are supplied: `none` supplies none, `append` supplies one
sorted list, and `each` supplies one invocation per sorted path.

Prepare rules may use `check` or `fix`; merge and release rules are check-only.
The release array is non-empty and is the one authoritative full-suite run
before a develop-to-main publication. A task must complete preparation before
one agent implementation commit; merge is performed only by the deterministic
`task_merge` operation.

## Safety boundaries

`cleanup.untracked_only` is always `true`. Cleanup paths are an explicit
allowlist of normalized repository-relative globs and never authorize tracked,
absolute, universal, or traversal paths. Generated rules declare input globs
and exact output paths; only the generated-output boundary may mutate those
outputs. No declaration command may use shell command-string evaluation such
as `sh -c`, `cmd /c`, or PowerShell `-Command`; commands are direct argv.

The declaration fails closed on unknown fields, unsafe paths, duplicate IDs or
outputs, invalid phase modes, invalid timeouts, malformed JSON, and unmatched
changed paths. The validator performs no command execution and has no external
dependencies. Compatibility scope is none. Adoption, a runner, a root
`quality-gates.json`, and generated-file mutation belong to a later explicitly
authorized slice.
