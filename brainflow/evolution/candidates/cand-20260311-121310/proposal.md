# Self-Rewrite Proposal

- proposal_id: proposal-20260311-121221
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_mitigation.json']

## Rationale
Add a procedural hint to avoid long CLI args by using temp files/stdin, reducing Windows arg-length risk without touching other files.

## Risks
['Low risk: adds a new procedural note file only; no runtime behavior changes.']

## Expected Benefit
['Reduced failures due to Windows CLI argument length limits in future procedural decisions.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
