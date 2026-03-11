# Self-Rewrite Proposal

- proposal_id: proposal-20260311-005955
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a small procedural config to centralize CLI argument-length safeguards without touching large files; keeps payloads file-based to reduce Windows command-line length risk.

## Risks
['If unused by callers, no effect. Consumers must read this policy to benefit.']

## Expected Benefit
['Provides a single authoritative policy that encourages file-based args, reducing Windows CLI arg-length failures.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
