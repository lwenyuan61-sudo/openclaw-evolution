# Self-Rewrite Proposal

- proposal_id: proposal-20260311-100212
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_policy.json']

## Rationale
Add a small procedural policy file to prefer file-based payloads and short CLI args, reducing Windows command-line length risk without touching existing code.

## Risks
['Policy file may be unused until referenced by workflows.']

## Expected Benefit
['Provides a lightweight, low-risk reference to guide future workflow edits toward shorter CLI arguments on Windows.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
