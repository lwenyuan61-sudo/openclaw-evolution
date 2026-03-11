# Self-Rewrite Proposal

- proposal_id: proposal-20260311-092142
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Introduce a lightweight procedural config to encourage shorter CLI invocations and payload indirection, reducing Windows command-line length risk without touching code.

## Risks
['Downstream components may ignore this policy if not yet implemented; no functional change unless read.']

## Expected Benefit
['Provides a clear, centralized policy for minimizing long CLI arguments, lowering risk of Windows command-line length errors when adopted.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
