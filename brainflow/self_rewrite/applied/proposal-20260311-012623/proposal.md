# Self-Rewrite Proposal

- proposal_id: proposal-20260311-012623
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/self_modify_payload_latest.json']

## Rationale
Shorten large free-text fields in the self-modify payload to reduce Windows CLI argument length risk while preserving intent and allowlist.

## Risks
['Low: only shortens descriptive text; no schema or allowlist changes.']

## Expected Benefit
['Slightly smaller payloads reduce CLI arg-length risk while keeping functional intent intact.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
