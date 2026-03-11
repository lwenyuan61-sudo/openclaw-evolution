# Self-Rewrite Proposal

- proposal_id: proposal-20260310-214624
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/self_modify_payload_latest.json']

## Rationale
Update self-modify payload to explicitly prefer file-based payloads to reduce Windows CLI arg-length risk while keeping scope unchanged.

## Risks
['Low: adds a new hint field; downstream consumers that ignore unknown fields are unaffected.']

## Expected Benefit
['Reduces likelihood of Windows CLI arg-length issues by signaling file-based payload preference.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
