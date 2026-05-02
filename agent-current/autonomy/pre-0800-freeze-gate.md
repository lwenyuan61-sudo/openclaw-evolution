# Pre-08:00 Freeze Gate

Purpose: between the pre-08:00 handoff and the first post-08:00 wake, avoid re-opening broad planning just because cron fires again.

## When this gate applies
- local time is still before 08:00
- `autonomy/pre-0800-handoff-2026-04-23-0645.md` already exists
- no new Lee instruction, blocker, or user-facing opportunity has appeared
- current focus is unchanged

## Default action
Treat the existing stop point as still valid.

That means the wake should usually do only three things:
1. confirm the focus still holds
2. confirm lowActivityWindow should remain true
3. keep cadence at 15m unless a stronger signal appears

## Do not do by default
- invent another new autonomy track
- rebuild the overnight summary from scratch
- restore 5m merely because a lightweight internal artifact was possible

## Escalation conditions
This gate can be bypassed only if one of these becomes true before 08:00:
- Lee gives a new direct instruction
- a real blocker appears that benefits from fast follow-up
- a clearly user-facing high-value opportunity appears
- the same focus suddenly shows a genuine sustained high-value streak rather than more internal bookkeeping

## Verification
This gate is useful only if the remaining pre-08:00 wakes can resume cheaply from the existing handoff instead of repeatedly re-planning the same transition.