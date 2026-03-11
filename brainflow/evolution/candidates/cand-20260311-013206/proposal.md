# Self-Rewrite Proposal

- proposal_id: proposal-20260311-012922
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Reduce Windows CLI arg-length risk by centralizing a short-arg policy in a procedural JSON file without touching code.

## Risks
['File may be unused until code reads it; no immediate behavioral change.']

## Expected Benefit
['Provides a documented, low-risk policy stub to guide future CLI payload handling and reduce arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
