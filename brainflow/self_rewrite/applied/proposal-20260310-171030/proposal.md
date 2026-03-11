# Self-Rewrite Proposal

- proposal_id: proposal-20260310-171030
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce semantic memory excerpt size to lower Windows CLI arg-length risk and lessen LLM reliance on local file content while keeping workflow behavior intact.

## Risks
['S', 'l', 'i', 'g', 'h', 't', 'l', 'y', ' ', 'l', 'e', 's', 's', ' ', 's', 'e', 'm', 'a', 'n', 't', 'i', 'c', ' ', 'c', 'o', 'n', 't', 'e', 'x', 't', ' ', 'f', 'o', 'r', ' ', 'v', 'a', 'l', 'u', 'e', '/', 'b', 'g', ' ', 's', 'e', 'l', 'e', 'c', 't', 'i', 'o', 'n', ' ', 'i', 'n', ' ', 's', 'o', 'm', 'e', ' ', 'r', 'u', 'n', 's', '.']

## Expected Benefit
['S', 'h', 'o', 'r', 't', 'e', 'r', ' ', 'p', 'r', 'o', 'm', 'p', 't', 's', ' ', 'r', 'e', 'd', 'u', 'c', 'e', ' ', 'C', 'L', 'I', ' ', 'a', 'r', 'g', '-', 'l', 'e', 'n', 'g', 't', 'h', ' ', 'r', 'i', 's', 'k', ' ', 'a', 'n', 'd', ' ', 'L', 'L', 'M', ' ', 'i', 'n', 'p', 'u', 't', ' ', 's', 'i', 'z', 'e', ',', ' ', 'i', 'm', 'p', 'r', 'o', 'v', 'i', 'n', 'g', ' ', 'r', 'e', 'l', 'i', 'a', 'b', 'i', 'l', 'i', 't', 'y', '.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
