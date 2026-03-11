# Self-Rewrite Proposal

- proposal_id: proposal-20260311-005422
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_prefs.json']

## Rationale
Introduce a small procedural config file to enforce file-based payload passing and shorter command lines, reducing Windows CLI arg-length risk without touching code.

## Risks
['May be unused until referenced by runtime; no functional change if ignored.']

## Expected Benefit
['Provides a standard place to read CLI-length safeguards, enabling future logic to avoid long command lines.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
