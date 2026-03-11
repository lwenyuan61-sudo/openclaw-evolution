# Self-Rewrite Proposal

- proposal_id: proposal-20260310-204022
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['memory/procedural/cli_arglength_policy.json']

## Rationale
Reduce Windows CLI argument-length risk by centralizing limits and preferring file-based inputs for long payloads; this is a low-risk procedural config addition under allowlist.

## Risks
['If consumers ignore this policy file, behavior will not change; minimal operational risk.']

## Expected Benefit
['Lower likelihood of Windows CLI failures due to argument length by encourself_evolution_stability_capability file-based inputs for large payloads.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
