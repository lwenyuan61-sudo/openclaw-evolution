# Self-Rewrite Proposal

- proposal_id: proposal-20260311-091623
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a small procedural policy to prefer file-based payloads over long CLI arguments to reduce Windows command length risk.

## Risks
['May require downstream readers to honor this new policy; if ignored, no change.']

## Expected Benefit
['Lower risk of Windows command line length errors by encouraging file-based payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
