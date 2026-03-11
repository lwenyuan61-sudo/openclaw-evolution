# Self-Rewrite Proposal

- proposal_id: proposal-20260310-183102
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce the size of semantic memory text injected into downstream LLM-ish steps to lower Windows CLI arg length risk and lessen dependence on large local file reads, while keeping some context.

## Risks
['Reduced semantic context might slightly degrade value_judge/bg_selector recommendations.']

## Expected Benefit
['Smaller prompt payloads reduce Windows command-line length failures and lessen dependency on large local file reads while preserving minimal context.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
