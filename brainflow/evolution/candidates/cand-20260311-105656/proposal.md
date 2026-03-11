# Self-Rewrite Proposal

- proposal_id: proposal-20260311-105321
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safe_defaults.json']

## Rationale
Add a procedural defaults file that forces file-based payloads and short CLI arguments to reduce Windows arg-length risk without touching code.

## Risks
['If downstream code ignores this defaults file, there may be no effect.']

## Expected Benefit
['Lower likelihood of Windows CLI argument-length failures by promoting file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
