# Self-Rewrite Proposal

- proposal_id: proposal-20260310-210151
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_io_policy.json']

## Rationale
Add a procedural guardrail to keep LLM prompts and tool inputs file-based and compact, reducing Windows CLI arg-length risk without touching code.

## Risks
['Procedure file may be ignored by older runners that do not consult procedural memory.']

## Expected Benefit
['Lower risk of Windows CLI arg-length failures and more consistent tool invocation behavior.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
