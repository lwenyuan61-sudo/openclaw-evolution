# Self-Rewrite Proposal

- proposal_id: proposal-20260310-213413
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_mitigation.json']

## Rationale
Add a small procedural config to prefer file-based prompt bundling over long CLI args, reducing Windows command-line length risk without touching other files.

## Risks
['Low. Adds a new procedural note only; no runtime logic change.']

## Expected Benefit
['Reduces likelihood of Windows CLI arg-length errors and improves execution robustness.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
