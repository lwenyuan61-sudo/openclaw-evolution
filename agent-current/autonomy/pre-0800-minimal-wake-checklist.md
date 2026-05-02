# Pre-08:00 Minimal Wake Checklist

Purpose: give remaining pre-08:00 cron wakes a tiny execution path so they can preserve continuity without reopening planning.

## Use this checklist only when
- local time is still before 08:00
- `autonomy/pre-0800-freeze-gate.md` applies
- no new Lee instruction, blocker, or Lee-facing opportunity has appeared

## Minimal steps
1. Confirm `currentFocus` still matches the continuity state.
2. Confirm `lowActivityWindow` stays `true`.
3. Confirm `recommendedCadence` stays `15m`.
4. Leave one small artifact only if it reduces the cost of the first post-08:00 wake; otherwise prefer no new branch of work.
5. Update continuity state only if something materially changed.

## Anti-spin rule
If this wake cannot point to a concrete reduction in future recovery cost, do not invent a new autonomy track just to satisfy activity.

## Verification
This checklist is working if the remaining pre-08:00 wakes can stay short, consistent, and quiet while preserving a clean handoff into the first post-08:00 cadence decision.
