# Self-Rewrite Proposal

- proposal_id: proposal-20260310-202442
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_guardrails.json']

## Rationale
Add a small procedural config to prefer file-backed payloads and limit inline argument sizes to reduce Windows CLI arg-length risk without touching code.

## Risks
['Config may be ignored if not yet wired into execution flow.']

## Expected Benefit
['Provides a clear, low-risk guardrail for avoiding oversized inline CLI arguments on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
