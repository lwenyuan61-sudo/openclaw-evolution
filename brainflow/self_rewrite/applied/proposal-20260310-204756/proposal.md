# Self-Rewrite Proposal

- proposal_id: proposal-20260310-204756
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Add a small procedural policy file to encourage file-based inputs and cap inline payload size, reducing Windows CLI arg-length risk without touching code paths.

## Risks
['If no component reads this policy yet, the change has no effect until wired in.']

## Expected Benefit
['Provides a low-risk, future-proof guardrail to reduce inline argument size and support file-based inputs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
