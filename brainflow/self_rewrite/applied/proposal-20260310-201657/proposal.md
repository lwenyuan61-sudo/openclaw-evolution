# Self-Rewrite Proposal

- proposal_id: proposal-20260310-201657
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arglen_mitigation.json']

## Rationale
Add a procedural config to prefer file-based payload handoff over long CLI arguments to reduce Windows arg-length risk without touching other files.

## Risks
['If the runtime does not consume this procedural config, it will have no effect until wired in.']

## Expected Benefit
['Reduces risk of Windows CLI arg-length failures by standardizing short-arg + temp-file payload usage.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
