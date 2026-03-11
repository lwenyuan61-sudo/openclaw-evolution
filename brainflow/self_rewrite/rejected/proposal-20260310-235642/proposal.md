# Self-Rewrite Proposal

- proposal_id: proposal-20260310-235642
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: []

## Rationale
Add a procedural guardrail that caps Windows CLI argument length and prefers temp-file payloads to avoid command-line overflow without touching other files.

## Risks
['If other components ignore this guard, no effect.', 'Some tools may not support response files; fallback required elsewhere.']

## Expected Benefit
['Fewer Windows CLI invocation failures caused by long argument strings; more reliable tool execution.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
