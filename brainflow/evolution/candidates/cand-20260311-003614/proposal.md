# Self-Rewrite Proposal

- proposal_id: proposal-20260311-003516
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_policy.json']

## Rationale
Add a procedural policy to minimize Windows CLI argument length risk by standardizing file-based payload passing.

## Risks
['If not yet consumed by runtime, policy may have no immediate effect.']

## Expected Benefit
['Reduces risk of Windows CLI arg-length errors by encouraging file-based payload passing.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
