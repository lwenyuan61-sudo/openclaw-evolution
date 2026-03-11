# Self-Rewrite Proposal

- proposal_id: proposal-20260310-215446
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_invocation_policy.json']

## Rationale
Add a procedural policy to reduce Windows CLI argument length risk by preferring file-based payloads and avoiding long inline args.

## Risks
['Policy may be unused if no consumer reads this file; no behavior change until integrated.']

## Expected Benefit
['Lowers risk of Windows command-line length failures when invoking LLMs by promoting file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
