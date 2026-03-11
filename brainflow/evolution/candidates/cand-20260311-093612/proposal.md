# Self-Rewrite Proposal

- proposal_id: proposal-20260311-093242
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_guard.json']

## Rationale
Add a small procedural guard to prefer file-based payloads to reduce Windows CLI arg-length risk without touching code.

## Risks
['May require follow-up wiring in code to consume this procedural setting; no behavior change until read by runtime.']

## Expected Benefit
['Provides a low-risk, file-based configuration hook to steer future changes away from long inline CLI arguments on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
