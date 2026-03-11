# Self-Rewrite Proposal

- proposal_id: proposal-20260310-170423
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/chat_deep.yaml']

## Rationale
Remove large inline search payload from echo output to reduce Windows command-line length risk while keeping search results logged to file.

## Risks
['Draft step no longer includes raw search payload inline; downstream consumers expecting RAW_SEARCH in echo output may lose that field.']

## Expected Benefit
['L', 'o', 'w', 'e', 'r', ' ', 'l', 'i', 'k', 'e', 'l', 'i', 'h', 'o', 'o', 'd', ' ', 'o', 'f', ' ', 'W', 'i', 'n', 'd', 'o', 'w', 's', ' ', 'C', 'L', 'I', ' ', 'a', 'r', 'g', '-', 't', 'o', 'o', '-', 'l', 'o', 'n', 'g', ' ', 'f', 'a', 'i', 'l', 'u', 'r', 'e', 's', ' ', 'a', 'n', 'd', ' ', 'l', 'e', 's', 's', ' ', 'r', 'e', 'l', 'i', 'a', 'n', 'c', 'e', ' ', 'o', 'n', ' ', 'l', 'a', 'r', 'g', 'e', ' ', 'i', 'n', 'l', 'i', 'n', 'e', ' ', 'p', 'a', 'y', 'l', 'o', 'a', 'd', 's', ' ', 'w', 'h', 'i', 'l', 'e', ' ', 'p', 'r', 'e', 's', 'e', 'r', 'v', 'i', 'n', 'g', ' ', 's', 'e', 'a', 'r', 'c', 'h', ' ', 'd', 'a', 't', 'a', ' ', 'i', 'n', ' ', 'f', 'o', 'r', 'a', 'g', 'e', '.', 'm', 'd', '.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
