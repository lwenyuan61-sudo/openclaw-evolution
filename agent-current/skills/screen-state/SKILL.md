---
name: screen-state
description: Capture the current screen state on this Windows machine, compute a stable screen hash, and optionally save a screenshot and JSON snapshot. Use when the assistant needs a lightweight desktop perception organ, wants to detect screen changes over time, or needs a current screen snapshot before local GUI reasoning.
---

# Screen State

Use the bundled Python script to capture the current screen, compute a lightweight screen hash, and optionally persist the image or JSON snapshot.

## Quick start

Capture the current screen state as JSON:

```powershell
python skills\screen-state\scripts\screen_state.py --write-json state\screen_state.json
```

Capture and also save an image:

```powershell
python skills\screen-state\scripts\screen_state.py --write-json state\screen_state.json --save-image state\screen_state.png
```

## Workflow

1. Run the script when current desktop state may matter.
2. Use the `screenHash` to detect whether the desktop changed since the last snapshot.
3. Save an image when later visual inspection or comparison is needed.

## Notes

- This is a read-only perception organ.
- The screen hash is computed from a downsampled image so it is lightweight and stable enough for change detection.
- Use `--save-image` only when the actual screenshot is worth keeping; hashing alone is cheaper.
