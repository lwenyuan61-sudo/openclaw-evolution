# Self-Rewrite Proposal

- proposal_id: proposal-20260311-000307
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a lightweight procedural policy to prefer short CLI argument usage and file-based payloads to reduce Windows command-line length failures without touching other files.

## Risks
['Policy may be unused until referenced by caller.', 'Thresholds may need tuning for specific tools.']

## Expected Benefit
['Lower likelihood of Windows command-line length errors by nudging toward file-based arguments.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
