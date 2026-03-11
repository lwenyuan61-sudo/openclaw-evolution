# Self-Rewrite Proposal

- proposal_id: proposal-20260311-011740
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Add a small procedural config to prefer passing large payloads by file path to reduce Windows CLI arg-length risk, without touching other files.

## Risks
['May be unused until referenced by callers; no functional change by itself.']

## Expected Benefit
['Provides a centralized, short config for CLI payload handling to reduce arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
