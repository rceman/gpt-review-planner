# Host Prerequisites

The planner keeps its primary source and unittest tooling dependency-free, but
the complete repository gate suite requires host-provided tools. A validating
host must provide Git, Bash, Python 3, and pytest available through Python:

```bash
git --version
bash --version
python3 --version
python3 -m pytest --version
```

`pytest` is a host validation prerequisite for this repository. It is not a
runtime dependency of projects reviewed by the planner.

## Debian and Ubuntu

```bash
sudo apt update
sudo apt install -y python3-pytest
```

Prefer the operating-system package over installing into system Python with
`sudo pip`. Do not mutate the repository to work around a missing host tool.
Automated agents must not assume sudo authorization. When sudo is unavailable,
report the exact missing prerequisite to the owner or machine operator.

After installation, rerun:

```bash
python3 -m pytest --version
python3 -m pytest -q
```

For runtime-upgrade or gateway integration work, the host preflight also records
installed and running runtime versions, process identities, the authoritative
remote branch/ref, and the protocol/MCP tool surface. These operational proofs
do not replace the repository's local gates.

Release tooling is planner-owned. When a reviewed project contains
`scripts/release.py`, validate its exact canonical synchronization before
release work:

```bash
python3 scripts/validate-release-tool-conformance.py \
  --release-script scripts/release.py \
  --ci-script scripts/check-github-ci.py
```
