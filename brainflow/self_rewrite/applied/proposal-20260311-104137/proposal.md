# Self-Rewrite Proposal

- proposal_id: proposal-20260311-104137
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a procedural config to mitigate Windows CLI arg-length risk by favoring response files and conservative arg size limits.

## Risks
['New config may be unused unless referenced by runtime; no functional impact until adopted.']

## Expected Benefit
['Provides a clear, centralized guardrail to reduce CLI arg-length failures on Windows and encourages safer execution patterns.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
