# Self-Rewrite Proposal

- proposal_id: proposal-20260310-171319
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce semantic memory payload size to lower Windows CLI arg-length risk and lessen LLM input dependence while keeping signal.

## Risks
['Less semantic context may slightly reduce quality of value/bg suggestions in some runs.']

## Expected Benefit
['S', 'm', 'a', 'l', 'l', 'e', 'r', ' ', 's', 'e', 'm', 'a', 'n', 't', 'i', 'c', ' ', 'p', 'a', 'y', 'l', 'o', 'a', 'd', ' ', 'r', 'e', 'd', 'u', 'c', 'e', 's', ' ', 'C', 'L', 'I', ' ', 'a', 'r', 'g', ' ', 'l', 'e', 'n', 'g', 't', 'h', ' ', 'r', 'i', 's', 'k', ' ', 'a', 'n', 'd', ' ', 'd', 'e', 'c', 'r', 'e', 'a', 's', 'e', 's', ' ', 'L', 'L', 'M', ' ', 'i', 'n', 'p', 'u', 't', ' ', 's', 'i', 'z', 'e', ',', ' ', 'i', 'm', 'p', 'r', 'o', 'v', 'i', 'n', 'g', ' ', 's', 't', 'a', 'b', 'i', 'l', 'i', 't', 'y', ' ', 'a', 'n', 'd', ' ', 'p', 'a', 'r', 's', 'e', ' ', 's', 'u', 'c', 'c', 'e', 's', 's', '.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
