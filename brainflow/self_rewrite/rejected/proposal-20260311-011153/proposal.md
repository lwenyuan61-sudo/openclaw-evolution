# Self-Rewrite Proposal

- proposal_id: proposal-20260311-011153
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a small procedural config to force file-based payload usage and cap inline CLI payload size, reducing Windows command-line length risk without touching larger files.

## Risks
['If existing tooling ignores this file, behavior may not change until wired in.']

## Expected Benefit
['Lower likelihood of Windows CLI arg-length failures during BrainFlow execution by standardizing file-based payload passing.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
