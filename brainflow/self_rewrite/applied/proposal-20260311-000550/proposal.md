# Self-Rewrite Proposal

- proposal_id: proposal-20260311-000550
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a small procedural guard to prefer file-based payloads and avoid long CLI arguments on Windows, reducing arg-length risk without touching other files.

## Risks
['If the guard is unused by current code, it has no effect until wired in.']

## Expected Benefit
['Provides a clear, minimal policy to shift large payloads to files, lowering chances of Windows arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
