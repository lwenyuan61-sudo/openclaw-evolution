# Self-Rewrite Proposal

- proposal_id: proposal-20260311-004910
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/self_modify_payload_latest.json']

## Rationale
Shorten payload strings to reduce Windows CLI argument-length risk without altering behavior.

## Risks
['Minimal: only shortens a descriptive string; no behavioral change intended.']

## Expected Benefit
['Slightly smaller payloads reduce Windows CLI arg-length risk.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
