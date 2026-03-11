# Self-Rewrite Proposal

- proposal_id: proposal-20260311-001730
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Shorten procedural payload fields to reduce downstream CLI argument length risk while preserving intent.

## Risks
['Minimal; only shortens text fields.']

## Expected Benefit
['Smaller payload reduces command-line argument length risk without changing behavior.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
