# Executable Patch Pack Format

An Executable Patch Pack is a repository-aware implementation handoff authored
primarily by GPT.

It must contain:

- normative behavior;
- exact file-level implementation;
- target-language tests;
- canonical fixtures;
- validation truth;
- local-agent execution instructions;
- acceptance gates;
- workflow and repository pins.

The local agent integrates and proves the patch. It does not reinterpret the feature.

## Exact file-scope invariant

The following sets must agree:

- `manifest.json` created, modified, and deleted paths;
- created and modified paths represented by `patch/changes.patch`;
- created and modified paths supplied by `overlay/`;
- `patch/delete-paths.txt`;
- the final repository diff from `target.base_revision`.

`changes.patch` paths are extracted through `git apply --numstat -z`, not by
manually splitting quoted `diff --git` headers. UTF-8 names, spaces, and embedded
whitespace therefore retain their exact repository spelling.

The final verifier preserves operation classes:

- `A` and untracked paths → created;
- `M` and `T` → modified;
- `D` → deleted;
- `R` → old path deleted and new path created;
- `C` → new path created.

Matching only the union of paths is insufficient. A manifest that declares a file
as modified must fail when the repository actually deletes it.

Every pack includes `DEVIATIONS.md` and `scripts/patch_pack_scope.py`. An undeclared
path or mismatched operation type is a blocking deviation, not an implicit
integration correction.
