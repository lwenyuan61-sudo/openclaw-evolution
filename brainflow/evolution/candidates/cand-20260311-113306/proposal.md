# Self-Rewrite Proposal

- proposal_id: proposal-20260311-113218
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_policy.json']

## Rationale
Add a procedural policy file to favor response-file style inputs and shorter CLI arguments, reducing Windows arg-length risk without touching code or reading additional files.

## Risks
['Policy file may be unused if not yet read by executors; no direct behavioral change without integration.']

## Expected Benefit
['Provides a low-risk, allowlisted procedural hook to guide future changes toward safer CLI invocation patterns on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
