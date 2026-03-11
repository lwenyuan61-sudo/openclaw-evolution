# Self-Rewrite Proposal

- proposal_id: proposal-20260311-114937
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a small procedural policy file to prefer file-based payloads over long CLI args, reducing Windows argument-length risk without touching other files.

## Risks
['Policy file may be ignored if not yet wired into workflow logic.']

## Expected Benefit
['Provides a clear, low-risk procedural directive to shift large inputs to files, lowering CLI arg-length failures on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
