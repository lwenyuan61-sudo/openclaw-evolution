# Self-Rewrite Proposal

- proposal_id: proposal-20260310-215702
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No file content loaded; to avoid unsafe full-file replacement and CLI arg-length risk, produce no edits.

## Risks
['No changes applied; underlying issue may persist.']

## Expected Benefit
Avoids risky blind overwrite and potential CLI arg-length errors.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
