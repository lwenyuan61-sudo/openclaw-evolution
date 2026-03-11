# Self-Rewrite Proposal

- proposal_id: proposal-20260311-102204
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/self_modify_payload_latest.json']

## Rationale
Shorten payload goal text to reduce Windows CLI argument-length risk while preserving intent.

## Risks
['Low: only shortens goal text; semantics preserved.']

## Expected Benefit
['Slightly lower CLI arg-length risk and reduced payload size.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
