# Self-Rewrite Proposal

- proposal_id: proposal-20260310-213910
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Introduce a lightweight procedural policy file to prefer file-based payloads and short CLI args on Windows, reducing arg-length risk without touching code.

## Risks
['If no component reads this policy yet, the change has no effect; benign.']

## Expected Benefit
['Provides a single-source policy that can be consulted to avoid long CLI arguments on Windows, reducing failure risk when adopted.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
