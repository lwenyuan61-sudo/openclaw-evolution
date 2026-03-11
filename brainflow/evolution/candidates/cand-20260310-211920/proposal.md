# Self-Rewrite Proposal

- proposal_id: proposal-20260310-211501
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a procedural guard to avoid long Windows CLI argument strings by standardizing on file-based payloads and temp-file handoff, reducing risk of command length failures without touching other code.

## Risks
['Minimal; new guideline may require downstream components to read this procedure for effect.']

## Expected Benefit
['Lower probability of Windows command-line length failures; more robust execution for large prompts or payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
