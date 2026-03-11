# Self-Rewrite Proposal

- proposal_id: proposal-20260311-120940
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_policy.json']

## Rationale
Introduce a procedural policy to minimize Windows CLI argument length risks by preferring stdin/temp-file payloads over large inline args.

## Risks
['New policy file may be unused unless referenced by executor logic.']

## Expected Benefit
['Provides a clear, low-risk guideline to reduce command-line length failures on Windows by standardizing file-based payload handling.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
