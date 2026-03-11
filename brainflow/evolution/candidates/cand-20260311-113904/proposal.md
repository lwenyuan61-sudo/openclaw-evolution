# Self-Rewrite Proposal

- proposal_id: proposal-20260311-113814
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_guard.json']

## Rationale
Add a small procedural config to prefer file-based IO to reduce Windows CLI arg-length risk without touching other files.

## Risks
['Low. Adds a new procedural rule file only.']

## Expected Benefit
['Reduces risk of Windows CLI arg-length failures by encouraging file-based payload passing.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
