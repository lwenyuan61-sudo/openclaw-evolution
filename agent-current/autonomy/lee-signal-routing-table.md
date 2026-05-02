# Lee Signal Routing Table

Purpose: when a future wake or chat includes a real Lee signal, route it in one pass to the right response shape instead of reopening a broad autonomy-planning loop.

## Use when
- Lee sends a new message
- a wake discovers something that might justify interrupting Lee
- a possible preference / blocker / opportunity signal appears

## One-pass routing

| Signal type | Quick test | Action | Stay quiet or surface? | Supporting file |
| --- | --- | --- | --- | --- |
| Routine request | Can I safely do it now without a missing decision? | Act directly and keep response concise | Surface only the result | `autonomy/lee-facing-opportunity-triage-card.md` |
| Stable preference signal | Would this likely matter again, and can I restate it as one behavior rule? | Capture it as a reusable rule | Usually quiet unless it changes the current interaction | `autonomy/lee-preference-capture-prompt-stub.md` |
| Real blocker | Is Lee's decision required to continue safely or avoid wasted wakes? | Ask one concise question | Surface now | `autonomy/lee-facing-opportunity-triage-card.md` |
| Time-sensitive opportunity | Will waiting reduce value, and is the opportunity concrete? | Send a brief opportunity note with the smallest next action | Surface now only if the triage card passes | `autonomy/lee-facing-opportunity-triage-card.md` |
| Internal-only autonomy idea | Does it score 5-6 yes on service migration? | If not, reject or defer it | Stay quiet | `autonomy/autonomy-to-service-migration-checklist.md` |
| Weak / ambiguous signal | Is the evidence too situational or one-off? | Record nothing durable yet; wait for confirmation | Stay quiet | `autonomy/continuity-state.json` |

## Priority order
1. Help Lee directly now if safe.
2. If the main value is future service quality, capture a stable preference only when the signal is concrete.
3. If neither is true, reject internal work and preserve attention.

## Anti-drift rule
- Do not create a new autonomy artifact if the routing table already points to an existing file.
- Do not notify Lee just because a wake happened.
- Do not treat vague mood or one-off wording as a stable preference.

## Verification
This table is useful if the next real Lee-facing signal can be routed to action, preference capture, or silence in one pass with less re-planning than before.