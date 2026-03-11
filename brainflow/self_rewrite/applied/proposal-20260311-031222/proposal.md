# Self-Rewrite Proposal

- proposal_id: proposal-20260311-031222
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/llm_io_policy.json']

## Rationale
Reduce Windows CLI arg-length risk by defining a procedural policy that routes large payloads through files instead of long inline arguments, keeping command lines short and stable.

## Risks
['Policy file may be ignored unless consuming code reads it; temporary directory may need creation by caller.']

## Expected Benefit
['Shorter CLI arguments reduce Windows command-line length failures and improve execution reliability.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
