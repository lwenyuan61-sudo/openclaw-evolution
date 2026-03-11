# Self-Rewrite Proposal

- proposal_id: proposal-20260310-215145
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_guard.json']

## Rationale
Add a procedural guard to prefer tempfiles for long payloads, reducing Windows CLI arg-length risk.

## Risks
['If consumers ignore this config, behavior will not change; if misread, could route small payloads to tempfiles unnecessarily.']

## Expected Benefit
['Lower chance of Windows command-line length overflow and fewer failed tool invocations.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
