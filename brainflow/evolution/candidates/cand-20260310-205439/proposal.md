# Self-Rewrite Proposal

- proposal_id: proposal-20260310-205416
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_policy.json']

## Rationale
Introduce a small procedural policy file to minimize Windows CLI argument length by preferring temp-file inputs over long inline args.

## Risks
['Policy file may be ignored if no consumer reads it yet.']

## Expected Benefit
['Reduces risk of Windows command-line length errors by formalizing a temp-file preference for long inputs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
