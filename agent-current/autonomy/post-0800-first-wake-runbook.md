# Post-08:00 First-Wake Runbook

Purpose: let the first wake after 08:00 make one clean cadence + direction + action decision from the existing morning handoff set, without reopening a broad planning loop.

## Use when
- local time has just crossed 08:00
- current focus is still unchanged
- no new direct Lee instruction has arrived

## Reuse only these inputs
1. `autonomy/continuity-state.json`
2. `autonomy/pre-0800-handoff-2026-04-23-0645.md`
3. `autonomy/post-0800-cadence-check.md`
4. `autonomy/post-0800-decision-scorecard.md`
5. `autonomy/post-0800-direction-shortlist.md`
6. `autonomy/post-0800-lee-friction-artifact-candidates.md`
7. `autonomy/lee-facing-opportunity-triage-card.md`

## One-pass execution
1. Confirm the same `currentFocus` still holds.
2. Use the scorecard to choose cadence once: `5m`, `15m`, or `30m`.
3. Unless there is real Lee-facing leverage, reject `5m`.
4. Default direction stays `工作流压缩与去摩擦` unless a stronger Lee-facing signal now exists.
5. Choose exactly one next artifact/action from the Lee-friction candidates, or a stronger real Lee-facing action if one is present.
6. Use the triage card to decide whether the result should stay quiet or justify a concise Lee-facing message.
7. Update continuity state and ledger with the decision, artifact, and next stop point.

## Default answer if conditions are still mixed
- cadence: `15m`
- direction: `工作流压缩与去摩擦`
- next action: use the highest valid Lee-friction candidate, not another cadence-only note
- notification stance: quiet unless the triage card clearly says interrupt

## Guardrails
- Do not rebuild the whole night from scratch.
- Do not create another cadence/freeze note unless it clearly unlocks Lee-facing leverage.
- Do not increase frequency just because the clock passed 08:00.

## Verification
This runbook is useful only if the first post-08:00 wake can finish its cadence/direction/action decision faster and with less re-planning than the pre-runbook path.