# Self-Rewrite Proposal

- proposal_id: proposal-20260311-091912
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_safety.json']

## Rationale
Add a small procedural config note to bias future steps toward file-based payloads, reducing Windows CLI arg-length risk without touching code.

## Risks
['May be ignored by code paths that do not consult procedural memory.']

## Expected Benefit
['Guides future workflow steps toward safer, shorter CLI calls, reducing arg-length failures on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
