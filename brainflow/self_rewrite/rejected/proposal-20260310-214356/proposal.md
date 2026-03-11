# Self-Rewrite Proposal

- proposal_id: proposal-20260310-214356
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a procedural note to prefer file-based payloads and shorten inline CLI arguments to reduce Windows arg-length risk without touching other files.

## Risks
['Low: introduces a new procedural note only.']

## Expected Benefit
['Reduces likelihood of Windows command line length errors and improves workflow robustness.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
