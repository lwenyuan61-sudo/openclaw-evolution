# Self-Rewrite Proposal

- proposal_id: proposal-20260311-005143
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Reduce Windows CLI argument-length risk by defining a simple policy to prefer temp files/stdin for large prompts, avoiding oversized inline args.

## Risks
['If no component reads this policy, behavior will not change.']

## Expected Benefit
['Provides a clear, centralized limit to guide future steps toward temp-file usage and reduce CLI failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
