# Self-Rewrite Proposal

- proposal_id: proposal-20260311-001353
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Add a small procedural policy file to cap Windows CLI argument length risk without touching existing code or reading other files.

## Risks
['Policy file may not be consumed yet by runtime; requires later integration.']

## Expected Benefit
['Documents a safe default limit and mitigation strategy, reducing risk of Windows command-line length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
