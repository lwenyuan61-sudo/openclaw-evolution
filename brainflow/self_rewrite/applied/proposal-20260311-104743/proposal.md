# Self-Rewrite Proposal

- proposal_id: proposal-20260311-104743
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_safety.json']

## Rationale
Add a procedural guard to prefer file-based argument passing to reduce Windows CLI length risk without touching other files.

## Risks
["May be ignored by components that don't read this procedural guidance until integrated."]

## Expected Benefit
['Lower likelihood of Windows CLI argument-length failures when large prompts or payloads are passed to executors.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
