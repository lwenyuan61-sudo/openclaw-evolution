# Self-Rewrite Proposal

- proposal_id: proposal-20260311-100451
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_guard.json']

## Rationale
Add a lightweight procedural guard to cap Windows CLI argument length and prefer file-based payloads, reducing risk without touching code or other files.

## Risks
['If unused by runtime, change is inert. If a different component expects a conflicting schema name, it may ignore this file.']

## Expected Benefit
['Provides a single source of truth for CLI arg-length limits and encourages file-based payloads to reduce Windows command-line failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
