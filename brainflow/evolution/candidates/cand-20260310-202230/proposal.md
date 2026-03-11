# Self-Rewrite Proposal

- proposal_id: proposal-20260310-202206
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_mitigation.json']

## Rationale
Add a small procedural config to reduce Windows CLI argument length by favoring file-based prompts and minimizing inline payloads.

## Risks
['May be unused unless referenced by workflow logic.']

## Expected Benefit
['Provides a clear, low-risk knob for future workflow logic to avoid long inline CLI arguments on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
