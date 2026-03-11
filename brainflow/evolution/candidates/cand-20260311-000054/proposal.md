# Self-Rewrite Proposal

- proposal_id: proposal-20260310-235920
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Reduce Windows CLI arg-length risk by standardizing payload-to-file usage and limiting inline prompt size via a small procedural config file.

## Risks
['May be ignored if no loader consumes this config; low risk as it is additive.']

## Expected Benefit
['Provides a single, small config artifact to guide future runs toward file-based payloads and shorter CLI arguments on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
