# Post-08:00 Cadence Re-evaluation Check

用于 low-activity window 结束后的第一轮判断，避免因为“已经到早上了”就机械恢复高频。

## Trigger
- Local time has crossed 08:00
- Current focus is unchanged
- No new direct instruction from Lee yet

## Required checks

### 1. Opportunity check
- Is there a real user-facing opportunity right now?
- Is there a blocker that benefits from fast follow-up?
- Has the same focus produced sustained high-value output across recent wakes?

If all three are no, do **not** restore 5m by default.

### 2. Recent value check
Use `autonomy/output-evaluation.md` on the most recent wakes:
- recent high-value streak >= 2 on the same focus -> 5m can be justified
- mixed / medium value -> prefer 15m
- low-value streak >= 3 -> keep or move toward 30m

### 3. Noise check
Ask: if Lee saw this cadence increase, would there be a clear reason tied to Lee value?
- If yes, document the reason
- If no, keep the slower cadence

## Decision ladder
- 5m: only if real opportunity or sustained high-value build streak exists
- 15m: default post-08:00 continuation when focus remains useful but urgency is still moderate
- 30m: if still mostly observing, repeating checks, or lacking new leverage

## Verification note
A time-window change alone is not a sufficient artifact for restoring higher frequency.
