# Self-Rewrite Proposal

- proposal_id: proposal-20260310-170034
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce Windows CLI arg length and LLM context size by shortening semantic memory snippet passed through the workflow; this lowers risk of arg-too-long failures and reduces dependency on large local file content.

## Risks
['Smaller semantic snippet may omit some context, potentially reducing LLM judgment quality in this run.']

## Expected Benefit
['L', 'o', 'w', 'e', 'r', ' ', 'r', 'i', 's', 'k', ' ', 'o', 'f', ' ', 'W', 'i', 'n', 'd', 'o', 'w', 's', ' ', 'c', 'o', 'm', 'm', 'a', 'n', 'd', '-', 'l', 'i', 'n', 'e', ' ', 'a', 'r', 'g', 'u', 'm', 'e', 'n', 't', ' ', 'l', 'e', 'n', 'g', 't', 'h', ' ', 'e', 'r', 'r', 'o', 'r', 's', ' ', 'a', 'n', 'd', ' ', 'r', 'e', 'd', 'u', 'c', 'e', 'd', ' ', 'L', 'L', 'M', ' ', 'd', 'e', 'p', 'e', 'n', 'd', 'e', 'n', 'c', 'e', ' ', 'o', 'n', ' ', 'l', 'a', 'r', 'g', 'e', ' ', 'l', 'o', 'c', 'a', 'l', ' ', 'f', 'i', 'l', 'e', ' ', 'c', 'o', 'n', 't', 'e', 'x', 't', ',', ' ', 'i', 'm', 'p', 'r', 'o', 'v', 'i', 'n', 'g', ' ', 'r', 'u', 'n', ' ', 's', 't', 'a', 'b', 'i', 'l', 'i', 't', 'y', '.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
