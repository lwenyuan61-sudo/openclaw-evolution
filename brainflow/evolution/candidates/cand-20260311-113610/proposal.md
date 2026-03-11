# Self-Rewrite Proposal

- proposal_id: proposal-20260311-113505
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_guard.json']

## Rationale
Add a procedural policy to avoid long CLI arguments by preferring file-based payloads and setting conservative inline limits. This reduces Windows arg-length risk without touching code.

## Risks
['Policy may be ignored by components that do not consult this file; no runtime effect until adopted.']

## Expected Benefit
['Provides a documented, low-risk guardrail for avoiding Windows CLI arg-length failures and encourages file-based payload usage.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
