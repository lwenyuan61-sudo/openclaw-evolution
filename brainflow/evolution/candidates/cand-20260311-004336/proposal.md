# Self-Rewrite Proposal

- proposal_id: proposal-20260311-004007
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_mitigation.json']

## Rationale
Introduce a minimal procedural config to prefer shorter CLI invocations, reducing Windows argument-length risk without touching code.

## Risks
['New file may be unused until referenced by workflow code.']

## Expected Benefit
['Provides a small, safe knob for future workflows to reduce long-argument failures on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
