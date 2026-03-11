# Self-Rewrite Proposal

- proposal_id: proposal-20260311-015208
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/windows_arglen_policy.json']

## Rationale
Add a procedural rule to prefer file-based payload passing on Windows to reduce CLI argument length failures without touching code.

## Risks
['Procedure may be ignored if no consumer uses it; requires downstream to honor policy.']

## Expected Benefit
['Reduces Windows CLI arg-length risk by codifying a file-based payload preference.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
