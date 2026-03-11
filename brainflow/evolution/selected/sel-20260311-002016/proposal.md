# Self-Rewrite Proposal

- proposal_id: proposal-20260310-184641
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/strategies.json']

## Rationale
Add an explicit strategy principle to minimize inline text and prefer file/path references, guiding LLM steps toward smaller payloads and reducing Windows CLI arg-length risks.

## Risks
['Additional principle is advisory and may not be honored uniformly by all plugins.']

## Expected Benefit
['Encourages smaller prompt payloads and less inline file content, reducing Windows arg-too-long failures and dependency on LLM reading large local files.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
