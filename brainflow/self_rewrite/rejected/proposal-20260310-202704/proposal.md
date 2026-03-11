# Self-Rewrite Proposal

- proposal_id: proposal-20260310-202704
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe single-file change can be proposed without reading additional local files. To avoid risky assumptions and keep within the one-edit constraint, no edits are included.

## Risks
['No immediate improvement applied.']

## Expected Benefit
Avoids introducing incorrect changes without sufficient context.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
