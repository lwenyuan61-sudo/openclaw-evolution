# Self-Rewrite Proposal

- proposal_id: proposal-20260311-101924
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arglen_guard.json']

## Rationale
Add a lightweight procedural config to encourage response-file usage and cap CLI arg length, reducing Windows command-line length risk without touching code or workflows.

## Risks
['Config may be unused if no component reads it yet.']

## Expected Benefit
['Provides a safe, centralized hint for future CLI construction to avoid Windows arg-length failures with minimal risk.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
