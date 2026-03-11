# Self-Rewrite Proposal

- proposal_id: proposal-20260311-112241
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Add a small procedural config to prefer response-file or stdin-based payloads to reduce Windows CLI arg-length risk without touching other files.

## Risks
['Minimal; introduces a new procedural note file only.']

## Expected Benefit
['Reduces risk of Windows command-line length overflow and improves execution reliability.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
