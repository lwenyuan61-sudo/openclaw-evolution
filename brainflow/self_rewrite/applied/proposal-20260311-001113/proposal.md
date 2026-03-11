# Self-Rewrite Proposal

- proposal_id: proposal-20260311-001113
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_guard.json']

## Rationale
Add a small procedural guard config that favors file-based payloads over long CLI args to reduce Windows command-line length risk.

## Risks
['Minimal; introduces a new procedural hint file that may be ignored if not yet wired.']

## Expected Benefit
['Reduces likelihood of Windows CLI arg-length failures by nudging workflows toward file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
