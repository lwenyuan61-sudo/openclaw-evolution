# Self-Rewrite Proposal

- proposal_id: proposal-20260310-210635
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_guard.json']

## Rationale
Add a small procedural config to cap CLI argument size via a local guard, reducing risk of Windows command-line length failures without touching code paths.

## Risks
['Downstream components may ignore this config if not yet wired; no functional change unless read by the executor.']

## Expected Benefit
['Provides a single source of truth for safe CLI argument limits to prevent intermittent Windows spawn failures when payloads are large.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
