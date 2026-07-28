# Agent Communication Language Contract

## Purpose

This document is the normative language contract for communication between GPT
and the local coding agent. It is independent of the language used by the
project owner when communicating with GPT.

## Directional language rules

The owner may communicate with GPT in any language. GPT may explain decisions,
reviews, and results to the owner in the language selected by the owner.

All local-agent-facing communication MUST be written in English. This includes:

- every final `## AGENT_HANDOFF` section;
- every generated `AGENT_PROMPT.md`;
- patch-pack application and integration instructions;
- implementation, correction, merge, post-merge cleanup, and release prompts;
- gate, CI, blocker, deviation, and failure-handling instructions;
- questions and clarifications addressed to the local agent.

The local agent MUST write all execution communication in English. This
includes progress updates, questions, blockers, deviations, command failures,
test and gate results, CI reports, merge and cleanup reports, release reports,
and final implementation reports.

The owner conversation language MUST NOT propagate into an agent-facing prompt
or execution report.

## No bilingual agent contracts

Agent-facing prompts and reports MUST NOT duplicate instructions in two languages.
An English `AGENT_HANDOFF` must not contain a second translated copy
of the same instructions before or after the English text. The complete
instructional content of `AGENT_HANDOFF` is English except for exact literals
allowed below.

## Allowed untranslated literals

The English-only rule does not require translating exact technical or
repository-controlled data. The following may remain in their original
language when required:

- file and directory names;
- branch and tag names;
- command arguments and command output;
- identifiers, API fields, schema values, and protocol literals;
- exact error messages and log excerpts;
- exact source excerpts and owner requirements that must remain byte-identical;
- user-visible product copy, localization resources, and domain fixtures;
- filenames containing non-English text.

Such literals must be embedded in otherwise English instructions or reports.

## Repository-content boundary

This contract governs communication with the local agent. It does not impose English on application UI text,
product documentation, localization files,
domain fixtures, user-provided content, or source material whose language is
part of the requirement. Repository content follows its project-specific
language and localization contract.

Agent-authored commit messages MUST be written in English unless the owner
explicitly approves a repository-specific exception.

## Handoff integration

Before sending a workflow response, GPT determines whether local-agent action
is required. When action is required, the final top-level section is
`## AGENT_HANDOFF`, its complete instructional content is English, and no prose
follows it.

The canonical no-action sentence remains:

```text
No agent action is required. Preserve the reported state and wait for the next owner instruction.
```

The canonical patch-pack sentence remains:

```text
Apply patch pack `<EXACT_ARCHIVE_FILENAME>` from the Downloads folder.
```

Every generated `AGENT_PROMPT.md` MUST be written in English. Exact archive filenames,
checksums, commands, and repository literals are preserved without translation.

## Merge, cleanup, and release integration

Every merge, exact-SHA CI, ancestry, remote-branch deletion, cleanup, release,
`MERGE_FINALIZED`, and `MERGE_CLEANUP_BLOCKED` instruction or report is English.
The post-merge cleanup and release contracts reference this language contract.

## Violations

A non-English or bilingual agent-facing instruction or execution report is a
workflow contract violation. Correct the communication artifact before using it
as the authoritative instruction or final execution evidence.

Do not rewrite published Git history solely to correct prose in an already
completed conversational report. The language violation does not by itself
invalidate independently verified production code or runtime evidence.
