# Self-Rewrite Proposal

- proposal_id: proposal-20260310-201950
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_limits.json']

## Rationale
Add a small procedural config to cap CLI argument length by preferring file-based payloads, reducing Windows arg-length risk without touching code.

## Risks
['May be ignored if no loader yet; otherwise low risk.']

## Expected Benefit
['Encourages shorter command lines and safer payload handling on Windows, reducing execution failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
