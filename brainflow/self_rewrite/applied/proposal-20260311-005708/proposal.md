# Self-Rewrite Proposal

- proposal_id: proposal-20260311-005708
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/windows_cli_policy.json']

## Rationale
Add a small procedural config to prefer response files/short args on Windows, reducing CLI arg-length risk without touching code.

## Risks
['May be ignored by tooling if not yet wired, yielding no effect.']

## Expected Benefit
['Provides a centralized policy hint for future CLI construction to minimize Windows command-line length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
