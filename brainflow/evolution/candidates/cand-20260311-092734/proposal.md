# Self-Rewrite Proposal

- proposal_id: proposal-20260311-092655
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_policy.json']

## Rationale
Add a small procedural config to prefer short argument passing to reduce Windows CLI arg-length risk without touching code.

## Risks
['None; adds a new procedural hint file only.']

## Expected Benefit
['Reduces likelihood of Windows command-line length issues while keeping behavior opt-in.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
