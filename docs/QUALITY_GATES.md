# Quality gates declaration

`quality-gates.json` is a repository-relative, dependency-free declaration for
deterministic prepare, merge, and release workflows. The declaration contract
and validator are complete. This planner checkout has adopted its root
`quality-gates.json`; adoption by another project remains an explicit project
decision.

Validate a declaration with:

```bash
python3 scripts/validate-quality-gates.py quality-gates.json
```

The canonical template is
[`templates/project/quality-gates.json`](../templates/project/quality-gates.json).
Its top-level fields are exactly `schema_version`,
`unmatched_changed_path`, `cleanup`, `generated`, `rules`, and `release`.

Launcher validation is Linux-only and uses strict bounded allowlists. Supported
profiles are exact `sh`, `dash`, and `bash` POSIX launchers; exact `python` and
`python3` launchers; and exact `node` and `nodejs` launchers. Every launcher
option before the first script, module, or file operand must be recognized by
its profile. Unknown options fail closed. `zsh`, `ksh`, `fish`, `python2`,
`pypy`, `pypy3`, Ruby, Perl, and known Windows shell launchers are unsupported
and rejected outright; their switches are not parsed. Each supported profile
also requires a proven script, module, or file operand, unless it is in an
explicitly declared self-contained informational or Node test mode. Implicit
stdin and interactive/REPL execution are forbidden.

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
in `inputs` and exact output paths in `outputs`; only the generated-output boundary
may mutate those outputs. For supported Linux launchers, no declaration
command may use shell command-string evaluation; commands are direct argv.
This check applies only to launcher options for the effective executable
before its first script, module, or file operand. At most one transparent `env`
prefix is allowed; nested `env` launchers are rejected. After that operand, tokens
are treated as arguments to the checked script or file and are not re-scanned
as launcher options; recognized launcher options that require a value are
consumed before the operand. Missing values and option-looking values fail
closed; if a legitimate value names a file beginning with `-`, use its
repository-relative `./-name` form. The exact `-` token after `--` is the stdin
sentinel, not a proven file operand, and is rejected.

The declaration fails closed on unknown fields, unsafe paths, duplicate IDs or
outputs, invalid phase modes, invalid timeouts, malformed JSON, and unmatched
changed paths. The validator performs no command execution and has no external
dependencies. Compatibility scope is none.

## B1 read-only planning

The bounded B1 selector validates an explicitly supplied declaration and emits
one deterministic execution plan without running any declared command:

```bash
python3 scripts/plan-quality-gates.py \
  --repo <repository> \
  --declaration quality-gates.json \
  --base <40-character-commit> \
  --phase prepare|merge \
  --target WORKTREE|<40-character-commit> \
  --output /external/quality-gate-plan.json
```

B1 derives committed or complete worktree changes, including non-ignored
untracked files, applies the case-sensitive repository-relative glob matcher,
projects selected commands and prepare-only generated actions, and records the
validated cleanup allowlist with `performed: false`. It performs no formatting,
testing, cleanup, generated-file write, index/worktree/ref mutation, network
operation, commit, or push. Output is written atomically outside the target
repository and contains no timestamp.

The B1 plan is an input for a later explicitly authorized B2 executor. B2 may
execute commands only under its own safety contract; B1 never executes the
declaration and does not claim that any gate completed.
