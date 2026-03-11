# Self-Rewrite Proposal

- proposal_id: proposal-20260310-203736
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe single-file full replacement available without reading target content; returning no-op change set to comply with constraints.

## Risks
['No changes applied; underlying issues remain.']

## Expected Benefit
Avoids risky overwrite while honoring constraints.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
