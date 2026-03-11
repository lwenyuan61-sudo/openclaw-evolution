# Self-Rewrite Proposal

- proposal_id: proposal-20260310-210857
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_policy.json']

## Rationale
Introduce a procedural policy to prefer file-based payloads and short temp paths to reduce Windows CLI arg-length risk without touching code.

## Risks
['Policy may be unused until referenced by workflow/code; no immediate effect.']

## Expected Benefit
['Provides a standard place to anchor CLI arg-length mitigation with minimal risk and no code changes.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
