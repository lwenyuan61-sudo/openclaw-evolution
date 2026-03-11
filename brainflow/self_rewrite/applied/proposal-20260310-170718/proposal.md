# Self-Rewrite Proposal

- proposal_id: proposal-20260310-170718
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce prompt size to lower Windows CLI arg-too-long risk and lessen LLM dependence on local file content by shortening semantic memory excerpt.

## Risks
['R', 'e', 'd', 'u', 'c', 'i', 'n', 'g', ' ', 's', 'e', 'm', 'a', 'n', 't', 'i', 'c', ' ', 'm', 'e', 'm', 'o', 'r', 'y', ' ', 'e', 'x', 'c', 'e', 'r', 'p', 't', ' ', 'm', 'a', 'y', ' ', 's', 'l', 'i', 'g', 'h', 't', 'l', 'y', ' ', 'l', 'o', 'w', 'e', 'r', ' ', 'c', 'o', 'n', 't', 'e', 'x', 't', ' ', 'q', 'u', 'a', 'l', 'i', 't', 'y', ' ', 'f', 'o', 'r', ' ', 'v', 'a', 'l', 'u', 'e', '/', 'b', 'g', ' ', 's', 'e', 'l', 'e', 'c', 't', 'i', 'o', 'n', ' ', 'i', 'n', ' ', 's', 'o', 'm', 'e', ' ', 'r', 'u', 'n', 's', '.']

## Expected Benefit
['S', 'h', 'o', 'r', 't', 'e', 'r', ' ', 'p', 'r', 'o', 'm', 'p', 't', 's', ' ', 'r', 'e', 'd', 'u', 'c', 'e', ' ', 'C', 'L', 'I', ' ', 'a', 'r', 'g', ' ', 'l', 'e', 'n', 'g', 't', 'h', ' ', 'r', 'i', 's', 'k', ' ', 'a', 'n', 'd', ' ', 'L', 'L', 'M', ' ', 'i', 'n', 'p', 'u', 't', ' ', 's', 'i', 'z', 'e', ',', ' ', 'i', 'm', 'p', 'r', 'o', 'v', 'i', 'n', 'g', ' ', 'r', 'e', 'l', 'i', 'a', 'b', 'i', 'l', 'i', 't', 'y', ' ', 'o', 'f', ' ', 'o', 'f', 'f', 'l', 'i', 'n', 'e', ' ', 'r', 'u', 'n', 's', '.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
