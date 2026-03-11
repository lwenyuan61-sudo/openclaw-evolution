# Self-Rewrite Proposal

- proposal_id: proposal-20260311-093832
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_policy.json']

## Rationale
Add a procedural policy to mitigate Windows CLI arg-length risks by preferring file-based inputs and shorter commands; satisfies allowlist and single-file edit constraint without reading other files.

## Risks
['May require additional file I/O steps, slightly increasing task overhead.']

## Expected Benefit
['Lower chance of Windows command-length failures and more robust CLI execution.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
