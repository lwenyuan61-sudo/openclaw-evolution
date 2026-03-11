# Self-Rewrite Proposal

- proposal_id: proposal-20260311-103027
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a procedural guardrail to prefer file-based payloads over long CLI arguments to reduce Windows arg-length risk without touching code.

## Risks
['Low: adds a new procedural note without enforcing behavior in code.']

## Expected Benefit
['Provides a clear guardrail to avoid long CLI args, reducing failures on Windows when large payloads are passed inline.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
