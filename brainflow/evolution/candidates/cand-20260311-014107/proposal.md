# Self-Rewrite Proposal

- proposal_id: proposal-20260311-013401
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_len_policy.json']

## Rationale
Add a small procedural config to prefer file-based inputs over long CLI arguments, reducing Windows arg-length risk without touching code.

## Risks
['Policy file may be ignored by components that do not consult procedural configs.']

## Expected Benefit
['Reduces Windows command-line length failures by encouraging file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
