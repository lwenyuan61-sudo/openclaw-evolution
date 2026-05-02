---
name: python-runtime
description: Use the local Python runtime on this Windows machine for safe, scriptable data analysis, file transformation, module probing, and small verified automation tasks. Use when the assistant needs a first-class Python toolchain wrapper rather than ad-hoc shell commands.
---

# Python Runtime

This skill wraps the local Python executable as a discoverable, auditable toolchain.

## Quick start

Probe Python and useful modules:

```powershell
python skills\python-runtime\scripts\python_runtime.py probe --write-json state\python_runtime\python_runtime_state.json
```

Run a small smoke test:

```powershell
python skills\python-runtime\scripts\python_runtime.py smoke-test --out-dir state\python_runtime\smoke_test
```

Run an existing Python script through the wrapper:

```powershell
python skills\python-runtime\scripts\python_runtime.py run-script path\to\script.py --timeout 120
```

## Good uses

- Local data analysis and CSV/JSON transformations.
- Excel/PDF/DOCX support checks and preparation.
- Reproducible state-file updates.
- Small benchmark or verification scripts.

## Limits and policy

- Prefer fresh output directories for generated artifacts.
- Do not run destructive filesystem scripts unless Lee explicitly approves.
- Long-running daemons require a watchdog/timeout.
- Package installation or environment changes require main-persona judgment.
