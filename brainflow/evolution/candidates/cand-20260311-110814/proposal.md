# Self-Rewrite Proposal

- proposal_id: proposal-20260311-110738
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_guard.json']

## Rationale
Add a procedural guard config to minimize Windows CLI arg-length risk by preferring file-based payloads and chunking, without touching other files.

## Risks
['New config file may be ignored by existing code until wired; no runtime effect until consumed.']

## Expected Benefit
['Provides a clear, low-risk hook for future logic to avoid long CLI arguments on Windows, reducing failure likelihood.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
