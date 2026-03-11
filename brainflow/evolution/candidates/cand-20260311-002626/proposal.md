# Self-Rewrite Proposal

- proposal_id: proposal-20260311-002600
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_invocation_defaults.json']

## Rationale
Reduce Windows CLI argument-length risk by standardizing LLM invocation to prefer payload files over long inline args, without touching code.

## Risks
['Downstream code may ignore or not yet consume this procedural defaults file; no behavior change until wired.']

## Expected Benefit
['Provides a centralized, low-risk default to minimize inline CLI args, reducing failure risk on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
