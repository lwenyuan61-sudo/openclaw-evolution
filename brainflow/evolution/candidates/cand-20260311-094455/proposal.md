# Self-Rewrite Proposal

- proposal_id: proposal-20260311-094423
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_safety.json']

## Rationale
Introduce a compact, centralized CLI-argument safety policy to reduce Windows command-line length risk without touching code or other files.

## Risks
['May require future code to read this policy before it has effect; truncation policy could drop context if applied blindly.']

## Expected Benefit
['Provides a compact policy anchor for future enforcement, lowering risk of Windows CLI arg-length failures and encouraging file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
