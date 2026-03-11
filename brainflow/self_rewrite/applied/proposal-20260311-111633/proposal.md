# Self-Rewrite Proposal

- proposal_id: proposal-20260311-111633
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_guard.json']

## Rationale
Add a small procedural guard that enforces file-based inputs to reduce Windows CLI argument-length risk without touching other files.

## Risks
['May be ignored if no loader consumes this new procedural file; otherwise low risk.']

## Expected Benefit
['Encourages short CLI args and file-based payloads, reducing failure due to Windows command-length limits.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
