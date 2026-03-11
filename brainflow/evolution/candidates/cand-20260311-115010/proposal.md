# Self-Rewrite Proposal

- proposal_id: proposal-20260311-114342
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_io_policy.json']

## Rationale
Add a procedural policy file to prefer file-based LLM IO and cap CLI arg usage, reducing Windows command-line length risk without touching code.

## Risks
['If code does not read this policy yet, this change has no immediate effect.']

## Expected Benefit
['Provides a single-source policy to guide safer LLM invocation with shorter CLI arguments.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
