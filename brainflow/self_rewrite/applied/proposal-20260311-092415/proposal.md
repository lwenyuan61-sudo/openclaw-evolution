# Self-Rewrite Proposal

- proposal_id: proposal-20260311-092415
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_limits.json']

## Rationale
Introduce a small procedural config to encourage stdin/file-based payloads and cap CLI arg size, reducing Windows command-line length risk without touching code.

## Risks
['If no code reads this config yet, it will be inert until integrated.']

## Expected Benefit
['Provides a centralized, lightweight constraint to guide future CLI payload handling toward safer, shorter commands on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
