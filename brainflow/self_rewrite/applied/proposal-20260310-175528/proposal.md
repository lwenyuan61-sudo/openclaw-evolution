# Self-Rewrite Proposal

- proposal_id: proposal-20260310-175528
- goal: Improve BrainFlow execution success: reduce LLM JSON parse failures; ensure doer-mode; make workflow robust and self-improving.
- allowlist: ['workflows/*.yaml', 'plugins/**/*.py', 'core/**/*.py', 'memory/procedural/*.json']
- files: ['workflows/idle_think_offline.yaml']

## Rationale
Reduce Windows CLI arg length risk and LLM dependence on local file reads by shrinking semantic memory ingestion in the offline workflow, which directly feeds multiple LLM steps.

## Risks
['Less semantic context may slightly reduce relevance of value/bg selection in offline mode.']

## Expected Benefit
['Shorter CLI args and reduced LLM local-file dependence, lowering arg-too-long and parse-failure risk in offline runs.']

## Verification Plan
1) python -m compileall -q <sandbox>
2) python -c "import sys; sys.path.insert(0, '<sandbox>'); import core.engine; print('import_ok')"

## Rollback Plan
- Restore from backup_dir created during promote
