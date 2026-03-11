# Self-Rewrite Proposal

- proposal_id: proposal-20260311-101400
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Introduce a procedural policy to minimize Windows CLI argument-length risks by preferring short command lines and response/temp files; single new file to avoid touching existing code.

## Risks
['Policy file may be unused if not wired into runtime; no behavioral change until referenced.']

## Expected Benefit
['Provides a clear, short configuration for future wiring to reduce CLI argument-length failures on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
