# Self-Rewrite Proposal

- proposal_id: proposal-20260311-102701
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_mitigation.json']

## Rationale
Add a small procedural config file to enable safer, shorter CLI argument usage without touching code; this reduces Windows arg-length risk while respecting the one-edit constraint.

## Risks
['May be ignored if no loader consumes this file; minimal risk as it is additive.']

## Expected Benefit
['Provides a low-risk, discoverable knob for future workflow code to read and avoid long CLI args.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
