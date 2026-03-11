# Self-Rewrite Proposal

- proposal_id: proposal-20260311-115744
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a small procedural policy file to constrain CLI argument length and prefer file-based inputs, reducing Windows command-line length risk without touching code.

## Risks
['May be ignored if not consulted by executor; no direct enforcement.']

## Expected Benefit
['Provides a clear procedural guideline to minimize command-line length failures and improve run reliability on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
