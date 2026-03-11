# Self-Rewrite Proposal

- proposal_id: proposal-20260311-120022
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_profile.json']

## Rationale
Reduce Windows CLI argument-length risk by centralizing long options into a minimal procedural JSON profile file, avoiding lengthy command-line strings.

## Risks
['If the profile is unused by current CLI wrappers, no effect until integrated.']

## Expected Benefit
['Lower risk of Windows command-line length limits causing failures; safer defaults for long arguments.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
