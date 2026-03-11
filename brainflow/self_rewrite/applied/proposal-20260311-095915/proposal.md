# Self-Rewrite Proposal

- proposal_id: proposal-20260311-095915
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_mitigation.json']

## Rationale
Add a small procedural policy file to ensure long prompts/args are passed via temp files instead of CLI args, reducing Windows command-line length risk without touching code.

## Risks
['Policy file may be ignored if no loader consumes it yet.']

## Expected Benefit
['Provides a documented, loadable policy to steer future changes toward using temp files/STDIN for large payloads, lowering Windows CLI length failure risk.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
