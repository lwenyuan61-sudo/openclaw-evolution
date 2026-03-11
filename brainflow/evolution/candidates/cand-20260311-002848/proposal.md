# Self-Rewrite Proposal

- proposal_id: proposal-20260311-002819
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglen_guard.json']

## Rationale
Add a procedural config to keep CLI payloads compact by preferring temp-file inputs and short flags, reducing Windows arg-length risk without touching other files.

## Risks
['New procedural file may be unused until referenced by a workflow; no behavioral change if not read.']

## Expected Benefit
['Provides a lightweight, low-risk guardrail to reduce command-line length failures once integrated.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
