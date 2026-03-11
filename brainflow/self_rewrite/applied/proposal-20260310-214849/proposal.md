# Self-Rewrite Proposal

- proposal_id: proposal-20260310-214849
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safe_defaults.json']

## Rationale
Add a minimal procedural config to prefer file-based payloads and short command lines, reducing Windows CLI argument-length risk without touching code.

## Risks
['Low. New config file may be unused until referenced; no behavior change unless consumed.']

## Expected Benefit
['Provides a clear, reusable procedural hint to keep CLI argument lengths short, lowering risk of Windows command-line failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
