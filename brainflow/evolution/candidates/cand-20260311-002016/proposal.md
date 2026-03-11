# Self-Rewrite Proposal

- proposal_id: proposal-20260311-001945
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Add a small procedural config to prefer file-based payloads and cap CLI arg size, reducing Windows command-length risk without touching code or other files.

## Risks
['Downstream components may ignore the new procedural config if not wired; no behavior change until consumed.']

## Expected Benefit
['Provides a clear, low-risk knob to shift payloads to files and cap CLI arg length, reducing Windows CLI failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
