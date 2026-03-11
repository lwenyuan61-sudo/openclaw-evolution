# Self-Rewrite Proposal

- proposal_id: proposal-20260311-003039
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Reduce Windows CLI arg-length risk by enforcing chunked argument handling and external payload file usage; choose procedural JSON to avoid touching code and keep a single full-file replacement.

## Risks
['If consumers of this config are not implemented, the file will be inert and no behavior change will occur.']

## Expected Benefit
['Clear, low-risk configuration to guide shorter CLI invocations and payload-file usage, lowering the probability of Windows command-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
