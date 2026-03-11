# Self-Rewrite Proposal

- proposal_id: proposal-20260310-204245
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_guard.json']

## Rationale
Add a small procedural config to encourage shorter commands and file-based inputs to reduce Windows CLI arg-length risk without touching existing workflow files.

## Risks
['Procedural guidance file may be ignored unless referenced by other logic.']

## Expected Benefit
['Provides a low-impact, reusable guardrail to reduce CLI arg-length errors on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
