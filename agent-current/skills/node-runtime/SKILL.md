---
name: node-runtime
description: Use the local Node.js runtime on this Windows machine for safe JSON processing, local JavaScript scripts, build/dev ecosystem checks, and browser-tooling support. Use when the assistant needs a first-class Node toolchain wrapper rather than ad-hoc shell commands.
---

# Node Runtime

This skill wraps the local Node.js executable as a discoverable, auditable toolchain.

## Quick start

Probe Node:

```powershell
node skills\node-runtime\scripts\node_runtime.js probe --write-json state\node_runtime\node_runtime_state.json
```

Run a smoke test:

```powershell
node skills\node-runtime\scripts\node_runtime.js smoke-test --out-dir state\node_runtime\smoke_test
```

Run an existing JS script through the wrapper:

```powershell
node skills\node-runtime\scripts\node_runtime.js run-script path\to\script.js --timeout 120
```

## Good uses

- JSON/state processing.
- Local JavaScript tooling checks.
- Browser/control infrastructure support.
- Small reproducible verification scripts.

## Limits and policy

- Node can hit V8 heap limits on large contexts; use explicit heap controls when needed.
- Avoid memory-heavy long-running processes without timeout/watchdog.
- External package installation requires main-persona judgment.
- Destructive filesystem scripts require explicit approval.
