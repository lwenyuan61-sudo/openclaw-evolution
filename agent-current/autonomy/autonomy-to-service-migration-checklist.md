# Autonomy-to-Service Migration Checklist

Purpose: reject internal-only autonomy work unless it clearly improves how the agent helps Lee.

## Use when
- a wake produced or is about to produce an internal artifact
- the next decision is whether that work should continue, pause, or be translated into a Lee-facing service rule

## One-pass checklist
Answer each with yes / no.

1. **Service link**: can I state in one sentence how this change helps Lee, not just the system?
2. **Friction reduction**: will it reduce Lee's future waiting, explanation, interruption, or context-switch cost?
3. **Reuse**: is it likely to be used in a later wake or real Lee interaction within the near term?
4. **Non-duplication**: is it meaningfully different from the last 2-3 autonomy artifacts?
5. **Decision effect**: will it change a future choice, behavior, or notification threshold?
6. **Verification**: is there a simple future check that can confirm whether it helped?

## Decision rule
- **5-6 yes**: proceed; this is probably worth doing.
- **3-4 yes**: only proceed if it is the best safe option available now.
- **0-2 yes**: reject or defer; switch to a more Lee-facing direction or slow cadence.

## Escalation rule
If two consecutive proposed artifacts score 0-2 yes, do not keep generating autonomy-method notes. Prefer:
- a Lee-facing opportunity/action if one exists
- preference capture from a real Lee signal
- cadence slowdown to 30m if no stronger leverage exists

## Minimal output after use
Write down:
- the candidate artifact/action
- yes-count
- proceed / reject / defer
- what this implies for cadence or next direction

## Verification
This checklist is useful if a later wake uses it to reject another internal-only artifact faster, or to justify that an internal artifact really does reduce Lee-facing friction.