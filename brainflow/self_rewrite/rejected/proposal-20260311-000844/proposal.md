# Self-Rewrite Proposal

- proposal_id: proposal-20260311-000844
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a small procedural config to cap CLI arg length and prefer temp-file payloads, reducing Windows command-line length risk without touching other files.

## Risks
['If unused by runtime, this has no effect.', 'If runtime expects a different schema name, it may ignore the file.']

## Expected Benefit
['Lower probability of Windows CLI arg-length failures by guiding payloads to tempfile usage.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
