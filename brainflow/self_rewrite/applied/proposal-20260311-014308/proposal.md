# Self-Rewrite Proposal

- proposal_id: proposal-20260311-014308
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arg_length_guard.json']

## Rationale
Add a small procedural guard to prefer short command forms and temp files, reducing Windows CLI arg-length risk without touching code.

## Risks
['If a downstream component expects inline JSON only, it may ignore this guidance until code is updated to read the procedure.']

## Expected Benefit
['Lower incidence of Windows CLI arg-length errors and more reliable execution when large prompts or payloads are used.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
