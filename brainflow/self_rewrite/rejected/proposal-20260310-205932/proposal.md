# Self-Rewrite Proposal

- proposal_id: proposal-20260310-205932
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe single-file full replacement can be produced without reading additional files; to avoid Windows CLI arg-length risk and comply with constraints, no edit is applied.

## Risks
['No improvement will be realized until a safe edit can be prepared.']

## Expected Benefit
Avoids unintended overwrites and CLI arg-length issues while remaining compliant with allowlist and max edit constraints.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
