# Self-Rewrite Proposal

- proposal_id: proposal-20260310-213647
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Add a tiny procedural policy file to steer BrainFlow toward shorter Windows CLI invocations without touching code; minimizes risk of long argument lists and avoids extra file reads.

## Risks
['Low. Adds a small policy file only; no code changes.']

## Expected Benefit
['Guidance to avoid long CLI argument strings on Windows and reduce failure risk.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
