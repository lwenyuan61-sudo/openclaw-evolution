# Self-Rewrite Proposal

- proposal_id: proposal-20260311-120345
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_guard.json']

## Rationale
Add a procedural guard to prefer temp files over long CLI args, reducing Windows command length risk without touching code.

## Risks
['If consumers do not read procedural guards, effect may be limited until wired in.']

## Expected Benefit
['Lower chance of command failure due to Windows arg-length limits while keeping changes isolated to procedural memory.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
