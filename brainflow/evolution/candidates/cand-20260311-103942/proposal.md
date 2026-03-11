# Self-Rewrite Proposal

- proposal_id: proposal-20260311-103609
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/windows_cli_args_guardrail.json']

## Rationale
Add a procedural guardrail to prefer temp files over long inline CLI arguments, reducing Windows arg-length failures without touching code.

## Risks
['New guardrail may be ignored if not consulted by current workflows.']

## Expected Benefit
['Reduces risk of Windows command-line length errors and improves execution reliability for large payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
