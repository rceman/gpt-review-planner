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

Every pack includes `DEVIATIONS.md` and `scripts/patch_pack_scope.py`. An undeclared
path is a blocking deviation, not an implicit integration correction.
