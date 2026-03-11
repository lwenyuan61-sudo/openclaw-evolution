# Self-Rewrite Proposal

- proposal_id: proposal-20260311-003252
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Reduce Windows CLI argument-length risk by introducing a small procedural config that enforces prompt/arg truncation limits without touching other files.

## Risks
['May truncate important context in rare cases; mitigated by tail strategy and conservative limits.']

## Expected Benefit
['Lower likelihood of Windows CLI failures due to long arguments while keeping behavior deterministic.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
