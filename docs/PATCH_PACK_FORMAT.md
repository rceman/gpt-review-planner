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
