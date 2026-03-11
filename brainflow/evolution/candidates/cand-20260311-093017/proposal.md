# Self-Rewrite Proposal

- proposal_id: proposal-20260311-092941
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_safety.json']

## Rationale
Create a small procedural config to bias execution toward file-based payloads and short CLI args, reducing Windows command-line length risk without touching other files.

## Risks
['New config file may be ignored until wired by code.']

## Expected Benefit
['Safer defaults for future execution paths that honor procedural config; reduces risk of oversized command-line arguments.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
