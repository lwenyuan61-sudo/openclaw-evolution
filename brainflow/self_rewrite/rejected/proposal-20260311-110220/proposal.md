# Self-Rewrite Proposal

- proposal_id: proposal-20260311-110220
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a procedural guardrail to prefer file-based payloads and avoid long CLI argument lists on Windows, reducing arg-length failure risk without touching code.

## Risks
['May require slight adjustments in callers to honor the procedure']

## Expected Benefit
['Lower chance of CLI arg-length errors on Windows and more reliable automation runs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
