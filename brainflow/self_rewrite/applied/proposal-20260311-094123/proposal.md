# Self-Rewrite Proposal

- proposal_id: proposal-20260311-094123
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_guard.json']

## Rationale
Add a small procedural guard to reduce Windows CLI arg-length risk by encouraging config via file inputs instead of long inline args.

## Risks
['New rule may require downstream tooling to honor it; otherwise no effect.']

## Expected Benefit
['Lower chance of Windows CLI failures due to long arguments; more robust execution.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
