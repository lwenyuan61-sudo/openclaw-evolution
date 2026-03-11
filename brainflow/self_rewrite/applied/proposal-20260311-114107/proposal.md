# Self-Rewrite Proposal

- proposal_id: proposal-20260311-114107
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a small procedural guard to prefer short argument passing and file-based payloads to reduce Windows CLI length risk, without reading any additional files.

## Risks
['Minimal; adds a new procedural note file only.']

## Expected Benefit
['Lower risk of Windows CLI arg-length failures by promoting file-based payload passing.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
