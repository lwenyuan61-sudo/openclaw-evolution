# Self-Rewrite Proposal

- proposal_id: proposal-20260310-203445
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_guard.json']

## Rationale
Add a small procedural guard note to prefer response files and short argv to reduce Windows CLI arg-length risk without touching other code or files.

## Risks
['Low; adds a new procedural note only. No runtime behavior changes.']

## Expected Benefit
['Provides clear guidance to avoid Windows command-line length failures and improves robustness for future modifications.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
