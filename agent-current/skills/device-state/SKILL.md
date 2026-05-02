---
name: device-state
description: Enumerate local cameras, audio input/output devices, and available TTS voices on this Windows machine, and optionally write a JSON body-state snapshot. Use when the assistant needs to inspect which local multimodal organs are currently available before camera, microphone, speaker, or voice-loop tasks.
---

# Device State

Use the bundled Python script to inspect the machine's currently available multimodal devices.

## Quick start

List local camera, audio, and voice devices:

```powershell
python skills\device-state\scripts\device_state.py
```

Write a JSON snapshot for later routing or debugging:

```powershell
python skills\device-state\scripts\device_state.py --write-json state\device_state.json
```

Scan more camera indexes if needed:

```powershell
python skills\device-state\scripts\device_state.py --max-camera-index 8
```

## Workflow

1. Run the script before multimodal work if device availability is uncertain.
2. Use the JSON summary to decide whether camera/audio/voice-loop flows are available.
3. Save a snapshot when debugging device drift or updating `core/body-state.json`.

## Notes

- The script is read-only; it does not capture photos or audio.
- Camera enumeration attempts indexes `0..max-camera-index`.
- Audio device names may render as mojibake in some terminals on Windows, but the JSON structure remains usable.
