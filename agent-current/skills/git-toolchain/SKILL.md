---
name: git-toolchain
description: Use local Git safely for status, diff, provenance, and reversible change review on this Windows machine. Use when the assistant needs a first-class Git wrapper with guardrails; destructive reset/clean/push operations require explicit approval.
---

# Git Toolchain

This skill wraps local Git for safe provenance and review.

## Quick start

Probe Git:

```powershell
python skills\git-toolchain\scripts\git_toolchain.py probe --write-json state\git_toolchain\git_toolchain_state.json
```

Create a safe status snapshot:

```powershell
python skills\git-toolchain\scripts\git_toolchain.py status --write-json state\git_toolchain\status_snapshot.json
```

Create a bounded diff summary:

```powershell
python skills\git-toolchain\scripts\git_toolchain.py diff-summary --max-chars 12000 --write-json state\git_toolchain\diff_summary.json
```

## Good uses

- Check modified/untracked files before/after changes.
- Keep provenance for local self-upgrade work.
- Review small diffs before commits.

## Limits and policy

- `git reset --hard`, `git clean`, force push, and network push require explicit Lee approval.
- This wrapper intentionally exposes read-only/status/diff operations by default.
- Do not commit/push on behalf of Lee unless specifically asked.
