# Self-Rewrite Proposal

- proposal_id: proposal-20260311-101631
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_args_policy.json']

## Rationale
Add a small procedural policy file to prefer file-based payloads and cap CLI arg size, reducing Windows command-line length risk without touching existing code.

## Risks
['Downstream components may not yet read this policy file.']

## Expected Benefit
['Provides a clear, low-risk configuration artifact to guide future updates toward file-based payloads and safer CLI usage.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
