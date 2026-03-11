# Self-Rewrite Proposal

- proposal_id: proposal-20260311-111932
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_guard.json']

## Rationale
Add a small procedural config to force shorter inline CLI arguments by preferring temp files and chunking, reducing Windows arg-length risk without touching other files.

## Risks
['Low. New config may be unused until wired; no runtime behavior change if not referenced.']

## Expected Benefit
['Provides a standard guardrail for future command construction to reduce Windows CLI arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
