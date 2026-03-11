# Self-Rewrite Proposal

- proposal_id: proposal-20260311-010905
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a procedural policy file that enforces shorter CLI argument usage and prefers file-based payloads to reduce Windows arg-length risk.

## Risks
['Introducing a new policy file may be ignored if not wired into runtime; no effect until referenced.']

## Expected Benefit
['Reduces likelihood of Windows CLI arg-length failures by codifying a low limit and file-based payload preference.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
