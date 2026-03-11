# Self-Rewrite Proposal

- proposal_id: proposal-20260311-010637
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe full-file replacement can be proposed without reading target files; avoiding risk of breaking workflow.

## Risks
['No change applied; existing CLI arg-length risk may persist.']

## Expected Benefit
Avoids introducing incorrect full-file replacements or schema drift.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
