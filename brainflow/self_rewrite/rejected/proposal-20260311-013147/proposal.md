# Self-Rewrite Proposal

- proposal_id: proposal-20260311-013147
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
No safe single-file replacement can be proposed without reading target files; returning no-op to respect constraints and avoid unintended changes.

## Risks
No change applied; underlying JSON parse issues may persist.

## Expected Benefit
Avoids risky modifications without context; maintains system stability.

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
