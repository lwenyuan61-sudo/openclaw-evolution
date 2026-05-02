# local-evolution-agent-agency-core

A curated export of the current the local evolution agent architecture for continuity-first, cron-free agency, self-recovery, resident background continuity, lightweight statistical learning, and local multimodal skills.

## Included

- **Core control plane**
  - `core/self-state.json`
  - `core/session-mode.json`
  - `core/attention-state.json`
  - `core/homeostasis.json`
  - `core/organ-registry.json`
  - `core/body-state.json`
  - `core/perception-state.json`
  - `core/action-state.json`
  - `core/learning-state.json`
  - `core/resident-config.json`
  - `core/agency-loop.md`
  - `core/event-routing.md`
  - `core/learning-loop.md`
  - `core/review-loop.md`
  - `core/consistency-check.md`
  - `core/wake-model.md`
  - `core/resident-loop.md`
  - `core/statistical-learning.md`
  - `core/signal-bus.md`
  - `core/reality-bridge.md`
  - `core/scripts/state_sync.py`
  - `core/scripts/consistency_check.py`
  - `core/scripts/learning_tick.py`
  - `core/scripts/learning_update.py`
  - `core/scripts/action_ranker.py`
  - `core/scripts/signal_probe.py`
  - `core/scripts/reality_action.py`
  - `core/scripts/resident_daemon.py`
- **Autonomy and wake integration**
  - `AUTONOMY.md`
  - `HEARTBEAT.md`
  - `BACKLOG.md`
  - selected `autonomy/` flow files
- **Skills / organs**
  - `camera-io`
  - `audio-io`
  - `voice-loop`
  - `device-state`
  - `screen-state`
  - `desktop-input`
  - `keyboard-input`
- **Packaged skills**
  - `dist/*.skill`

## What this repo is for

This repo captures the current file-link architecture that turns a trigger-based assistant into a more continuity-driven, body-aware, learning-capable, cron-free agent:

`self-state -> mode -> attention -> homeostasis -> organ/body awareness -> continuity -> routing -> ranked smallest effective action -> verification -> learning/write-back`

## Publishing scope

This export intentionally omits personal memory, private user context, chat logs, transient runtime files, and unrelated workspace material. It is meant to publish the architecture, connection style, and skills without dumping the entire private workspace.

## Notes

- `voice-loop` is self-contained in this export and no longer depends on another skill folder at runtime.
- `device-state` is a lightweight read-only organ for inspecting local camera/audio/voice availability.
- `screen-state` is a lightweight read-only organ for capturing a stable desktop hash and screenshot snapshot.
- The control plane is intentionally cron-free by default; continuity is expected to come from state restoration plus heartbeat/direct/local events rather than scheduled self-spin.
- A resident background loop is included as a low-cost substrate for runtime continuity, self-checks, signal probing, and learning ticks; it is not meant to pretend to be infinite full-thought reasoning.
- Statistical learning is upgraded from plain logging to lightweight weights that can influence action ranking and skill bias.
- A local signal bus is included so real desktop/device/workspace changes can accumulate as routable signals.
- A reality bridge is included so perception can transition into small, reversible, auditable desktop actions instead of staying purely observational.
- The JSON state files represent a live working configuration, not a generic framework API.
- The multimodal skills target local Windows usage and rely on the Python packages used in the original workspace.
