# Self-Rewrite Proposal

- proposal_id: proposal-20260310-214136
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a small procedural guardrail to reduce Windows CLI arg-length risk without touching code; keeps future tooling from constructing oversized command lines.

## Risks
['Low; adds a new procedural config file only. No runtime behavior change until consumed by tooling.']

## Expected Benefit
['Provides a clear limit and guidance for avoiding Windows CLI arg-length failures, improving execution reliability.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
