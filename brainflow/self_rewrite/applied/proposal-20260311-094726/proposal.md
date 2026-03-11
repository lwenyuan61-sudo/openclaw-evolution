# Self-Rewrite Proposal

- proposal_id: proposal-20260311-094726
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/windows_cli_arglen_guard.json']

## Rationale
Add a procedural guard to minimize Windows CLI argument length failures by preferring file-based inputs over long inline arguments.

## Risks
['If downstream components do not consume procedural rules, this change will have no effect.']

## Expected Benefit
['Reduces Windows CLI arg-length errors by guiding workflows to use file-based inputs for large payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
