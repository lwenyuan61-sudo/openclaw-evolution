# Self-Rewrite Proposal

- proposal_id: proposal-20260310-212132
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a small procedural guardrail to minimize Windows command-line length risk by preferring file-based payloads and enforcing a max arg length threshold.

## Risks
['If no component reads this config yet, the change will have no effect until integrated.']

## Expected Benefit
['Reduces CLI failures on Windows by steering long payloads away from command-line arguments.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
