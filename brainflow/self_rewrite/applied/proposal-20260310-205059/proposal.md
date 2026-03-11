# Self-Rewrite Proposal

- proposal_id: proposal-20260310-205059
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a small procedural policy file that instructs the system to prefer file-based payloads when arguments are large, reducing Windows CLI arg-length risk without touching code.

## Risks
['If any executor ignores this policy file, behavior will be unchanged.']

## Expected Benefit
['Reduced risk of Windows CLI argument-length errors while keeping changes localized to a single, small procedural config file.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
