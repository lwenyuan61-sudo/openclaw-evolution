# Self-Rewrite Proposal

- proposal_id: proposal-20260311-110456
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/arg_length_guard.json']

## Rationale
Add a small procedural guard config to reduce Windows CLI argument-length risk without touching code paths; keeps payloads short by default and encourages file-based inputs.

## Risks
['Guard config may be ignored if no consumer reads it; however it is non-invasive and safe.']

## Expected Benefit
['Provides a clear, low-risk directive to keep CLI args short, lowering the chance of Windows command-line length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
