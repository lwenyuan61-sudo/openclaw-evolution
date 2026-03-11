# Self-Rewrite Proposal

- proposal_id: proposal-20260311-105925
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_invocation_policy.json']

## Rationale
Reduce Windows CLI arg-length risk by switching LLM invocation to file-based payloads and minimizing inline prompt size in a centralized procedural config.

## Risks
['If consumers do not read this policy file, no behavior change; if they do and require inline prompts, they may truncate overly long prompts.']

## Expected Benefit
['Lower likelihood of Windows CLI arg-length failures and more reliable LLM execution with large payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
