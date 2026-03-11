# Self-Rewrite Proposal

- proposal_id: proposal-20260310-210414
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Introduce a concise procedural rule to prefer file-based payloads and temp files over long inline CLI args, reducing Windows arg-length risk.

## Risks
['New procedural file may be unused until referenced by workflow logic.']

## Expected Benefit
['Reduced likelihood of Windows CLI arg-length failures without modifying core logic.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
