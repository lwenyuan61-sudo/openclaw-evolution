# Self-Rewrite Proposal

- proposal_id: proposal-20260311-010239
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Add a small procedural policy file to encourage short CLI invocations and file-based inputs on Windows, reducing arg-length risk without touching code.

## Risks
['May be ignored by components that do not consume procedural policy files.']

## Expected Benefit
['Provides a lightweight, centralized guideline to reduce Windows CLI arg-length failures with minimal change surface.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
