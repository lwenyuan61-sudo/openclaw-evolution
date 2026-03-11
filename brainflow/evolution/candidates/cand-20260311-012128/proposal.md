# Self-Rewrite Proposal

- proposal_id: proposal-20260311-012015
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Introduce a concise procedural config to keep CLI arguments short and favor file-based payloads to reduce Windows command-length risk without touching code.

## Risks
['New policy file may be unused until referenced; no behavior change if not read.']

## Expected Benefit
['Enables short-arg conventions and future hooks to avoid Windows CLI arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
