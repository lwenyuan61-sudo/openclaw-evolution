---
name: camera-io
description: Capture still images from local cameras and enumerate available camera devices on this Windows machine. Use when the assistant needs to inspect the physical world through a webcam, save a photo for later vision analysis, verify which camera index works, or build camera-based local automation.
---

# Camera IO

Use the bundled Python script to list usable cameras and capture a still image.

## Quick start

List available camera indexes:

```powershell
python skills\camera-io\scripts\camera_io.py list
```

Capture one frame from the default camera:

```powershell
python skills\camera-io\scripts\camera_io.py capture state\camera.png --device 0
```

Capture with a requested resolution:

```powershell
python skills\camera-io\scripts\camera_io.py capture state\camera_hd.png --device 0 --width 1280 --height 720
```

## Workflow

1. Run `list` to discover which indexes open successfully.
2. Capture to a named file under `state\` or another explicit path.
3. Use the saved image for follow-up inspection or vision analysis.
4. Prefer single-frame captures first; only add continuous capture later if truly needed.

## Notes

- The script currently targets still-image capture only.
- Output is written with OpenCV; use `.png` or `.jpg` paths.
- If a device opens but ignores the requested resolution, trust the reported width/height in the JSON output.
