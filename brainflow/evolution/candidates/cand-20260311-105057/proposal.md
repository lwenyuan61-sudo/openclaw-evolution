# Self-Rewrite Proposal

- proposal_id: proposal-20260311-105016
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_guard.json']

## Rationale
Add a small procedural config stub to encourage shorter CLI invocations and reduce Windows arg-length risk without touching large files.

## Risks
['If unused by runtime, change has no effect.']

## Expected Benefit
['Provides a lightweight, local reference to favor file-based payloads and shorter CLI argument usage, reducing risk of Windows arg-length errors.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
