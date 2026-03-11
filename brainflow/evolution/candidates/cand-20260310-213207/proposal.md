# Self-Rewrite Proposal

- proposal_id: proposal-20260310-212408
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_safety.json']

## Rationale
Add a procedural config hint to prefer file-based payloads to reduce Windows CLI arg-length risk without touching code.

## Risks
['Low: adds a new procedural hint file only; no runtime behavior change unless consumed.']

## Expected Benefit
['Provides a safe default to avoid command-line length failures on Windows when large JSON payloads are needed.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
