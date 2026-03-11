# Self-Rewrite Proposal

- proposal_id: proposal-20260311-014553
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a procedural guard to cap payload size for Windows CLI to reduce arg-length failures without touching code.

## Risks
['New guard may truncate context if not yet enforced by runtime; requires downstream support to honor this file.']

## Expected Benefit
['Lower risk of Windows command-line length errors and improved reliability of CLI invocations.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
