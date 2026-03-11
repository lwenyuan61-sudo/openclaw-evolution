# Self-Rewrite Proposal

- proposal_id: proposal-20260310-204518
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe full-file replacement possible without reading target file; returning no-op to avoid unintended changes and reduce risk.

## Risks
['No changes applied; underlying issues remain.']

## Expected Benefit
Avoids accidental corruption when full-file replacement is required without file context.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
