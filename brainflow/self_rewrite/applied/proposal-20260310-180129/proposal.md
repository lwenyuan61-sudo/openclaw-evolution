# Self-Rewrite Proposal

- proposal_id: proposal-20260310-180129
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce large inline objects in candidate payloads to minimize Windows CLI arg-length failures and lessen LLM exposure to bulky local data; keep only the acc hash needed for dedup/debug.

## Risks
['Downstream consumers expecting full acc object in thought_packet will no longer receive it; they should rely on run_packet for details.']

## Expected Benefit
['Smaller candidate payloads reduce Windows CLI arg-length failures and lower chances of LLM parse issues triggered by oversized inputs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
