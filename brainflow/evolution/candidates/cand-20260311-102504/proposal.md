# Self-Rewrite Proposal

- proposal_id: proposal-20260311-102434
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Add a procedural policy to enforce short CLI arguments by routing large payloads through temp files to reduce Windows arg-length failures.

## Risks
['Requires runtime adoption by callers; unused policy file alone has no effect until referenced.']

## Expected Benefit
['Provides a clear, centralized threshold to avoid Windows CLI arg-length limits and reduce command failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
