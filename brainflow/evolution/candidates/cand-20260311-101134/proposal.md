# Self-Rewrite Proposal

- proposal_id: proposal-20260311-101019
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_policy.json']

## Rationale
Add a procedural guardrail to avoid long CLI arguments by encouraging file-based payloads and short command lines, reducing Windows arg-length risk.

## Risks
['New policy file may be unused unless referenced by workflows or code.']

## Expected Benefit
['Provides a clear procedural guideline to reduce long-arg failures on Windows and improve execution reliability.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
