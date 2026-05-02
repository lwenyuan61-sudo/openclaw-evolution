# Usage Governor

Purpose: keep Lee's Codex/OpenClaw quota available while still allowing continuous self-evolution.

## Visibility

The main persona can inspect current model/quota signals with `session_status`.
As of 2026-05-01 23:53 AEST, visible quota signals were:

- Week left: 38%
- Weekly reset: about 3d 17h away
- Current window left: 58% / about 2h 12m
- Context: 59k / 200k
- Queue depth: 2

If exact account/provider billing APIs are unavailable, treat `session_status` as the authoritative visible quota signal and write snapshots to `state/codex_usage_governor_status.json`.

## Reserve rule

Always preserve at least **10% weekly quota** for Lee's direct, urgent, or interactive use.

## Speed bands

- `fast-normal` when weeklyLeftPercent >= 35: autonomous work may continue, but prefer one verified connector per wake and batch non-urgent reports.
- `measured` when 20 <= weeklyLeftPercent < 35: avoid speculative deep runs; prefer small local scripts, exact edits, and one regression gate.
- `conserve` when 10 < weeklyLeftPercent < 20: only direct Lee requests, blockers, service recovery, or high-value reversible maintenance.
- `reserve-lock` when weeklyLeftPercent <= 10: stop autonomous evolution except urgent gateway/service recovery or explicit Lee instruction.

## Before expensive actions

Check `session_status` before:

- spawning subagents / ACP sessions
- long matrix or repeated regression runs
- deep research / browser loops
- high-token summarization or large file reads
- any repeated autonomous wake burst

Use the smaller useful gate first. Prefer local scripts and state-file audits over long model reasoning when possible.
