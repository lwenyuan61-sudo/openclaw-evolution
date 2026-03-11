# Self-Rewrite Proposal

- proposal_id: proposal-20260311-012327
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_guard.json']

## Rationale
Add a concise procedural guard to prefer file-based payloads over long CLI arguments on Windows, reducing arg-length risk without touching other files.

## Risks
['Low: introduces a new small procedural file; no runtime behavior changes unless referenced.']

## Expected Benefit
['Lower chance of Windows CLI argument-length failures by documenting a safe default for long inputs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
