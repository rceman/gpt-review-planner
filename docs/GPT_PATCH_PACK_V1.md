# GPT Patch Pack v1

## Status

This is the only supported executable patch-pack format.

Compatibility scope: none  
Compatibility authorization: not granted  
Canonical implementation: GPT Patch Pack v1 archive plus standard runner  
Legacy behavior: unsupported and out of scope

## Archive

A deterministic `.tar.gz` contains exactly one root:

```text
<root>/
├── MANIFEST.json
├── SHA256SUMS
├── AGENT_TASK.md
└── payload/
    └── changes.patch
```

Every regular file except `SHA256SUMS` is checksummed. Absolute paths,
traversal, links, devices, duplicate members, case-fold collisions,
unchecksummed files, and unsafe permissions are rejected.

## Manifest

`schema_version` is `2` and `format` is `gpt-patch-pack-v1`. The manifest fixes:

- pack identity and runner version;
- planner workflow pin and evidence directory;
- repository slug, accepted origin URLs, branch, base, remote, and remote ref;
- canonical payload argv arrays and success marker;
- exact created, modified, and deleted paths;
- verified target Git tree;
- ordered gate argv arrays, timeouts, and output limits;
- requirements and compatibility declaration.

Unknown fields fail. Paths are normalized relative POSIX paths. Commands are
argv arrays and never shell-interpolated.

## Execution

1. Verify outer archive SHA-256.
2. Safely extract one root.
3. Verify exact checksum coverage.
4. Strictly validate the manifest.
5. Verify origin, branch, local HEAD, clean status, remote HEAD, and base.
6. Create detached worktree A.
7. Run payload preflight and prove it made no changes.
8. Apply payload and require its marker.
9. Run every gate in order.
10. Stage all changes, verify operation classes and target tree.
11. Generate a full-index binary patch.
12. Replay it in detached worktree B.
13. Compare target trees and rerun every gate.
14. Recheck the real checkout.
15. Only with explicit `--apply`, apply the verified patch to the real checkout.
16. Compare the real tree and leave changes unstaged.
17. On apply failure, restore the exact clean base and declared created paths.

Failures before real apply never change the real checkout.

## Markers

```text
PACK_VERIFIED pack_id=<id> target_tree=<tree>
REAL_WORKTREE_UNCHANGED
```

With explicit apply:

```text
GPT_PATCH_PACK_APPLIED pack_id=<id> target_tree=<same-tree>
```

## Builder

`scripts/build-gpt-patch-pack-v1.py` is the sole builder. It consumes an exact
full-index binary patch, task, requirements, and gate plan; computes the target
tree in isolation; builds the deterministic archive and sidecar; and invokes
the standard runner before publication.

## Unsupported

Directory packs, overlays, transform runners, reader scripts, repository or
branch selection by the payload, `AGENT_PROMPT.md`, auto-detection, negotiation,
migration commands, compatibility flags, aliases, and legacy readers are
unsupported.

## Evidence

The existing two-commit model remains. Evidence records compatibility scope,
authorization, and exact compatibility/legacy/fallback/migration arrays. The
verifier rejects non-empty arrays without explicit authorization.

## Release gate

Changes to runner, builder, schema, template, delivery validator, or format docs
must pass a synthetic add/modify/delete pack end-to-end and print matching
`PACK_VERIFIED` and `GPT_PATCH_PACK_APPLIED` target trees.
