---
name: desktop-input
description: Unified Windows desktop control via local Python Win32 calls. Use when the assistant needs to capture the screen, inspect desktop state, move the mouse, click, drag, scroll, type text, or send keyboard shortcuts on this Windows machine. Best for simple local GUI automation when command-line control is not enough.
---

# Desktop Input

Use the bundled Python scripts for local Windows desktop control actions, including screen capture, mouse, and keyboard.

## Workflow

1. Prefer the smallest reversible action first.
2. Read current cursor position before moving when precision matters.
3. Use absolute coordinates unless a relative move is clearly safer.
4. For risky GUI actions, narrate briefly and keep steps minimal.
5. After action, verify by reading cursor position again or by the user-visible effect when possible.

## Scripts

### Mouse / pointer / click actions
```powershell
python skills\desktop-input\scripts\desktop_input.py <action> [args]
```

### Keyboard actions
```powershell
python skills\desktop-input\scripts\keyboard_input.py <action> [args]
```

### Screen capture
```powershell
python skills\desktop-input\scripts\screen_capture.py <output-path>
```

## Actions

### Get cursor position
```powershell
python skills\desktop-input\scripts\desktop_input.py pos
```

### Move mouse absolute
```powershell
python skills\desktop-input\scripts\desktop_input.py move --x 100 --y 200
```

### Move mouse relative
```powershell
python skills\desktop-input\scripts\desktop_input.py move-rel --dx 10 --dy -5
```

### Left click
```powershell
python skills\desktop-input\scripts\desktop_input.py click
```

### Double click
```powershell
python skills\desktop-input\scripts\desktop_input.py double-click
```

### Right click
```powershell
python skills\desktop-input\scripts\desktop_input.py right-click
```

### Drag
```powershell
python skills\desktop-input\scripts\desktop_input.py drag --x 400 --y 500
```

### Scroll
```powershell
python skills\desktop-input\scripts\desktop_input.py scroll --amount 120
```

### Move and click
```powershell
python skills\desktop-input\scripts\desktop_input.py move-click --x 400 --y 500
```

### Delay then click
```powershell
python skills\desktop-input\scripts\desktop_input.py delay-click --seconds 2
```

### Type text
```powershell
python skills\desktop-input\scripts\keyboard_input.py type --text "hello"
```

### Single key
```powershell
python skills\desktop-input\scripts\keyboard_input.py key --name enter
```

### Hotkey
```powershell
python skills\desktop-input\scripts\keyboard_input.py hotkey --keys ctrl,s
```

### Capture screen
```powershell
python skills\desktop-input\scripts\screen_capture.py state\screen.bmp
```

## Notes

- This skill is local-machine only.
- Coordinates are screen coordinates.
- Start with `pos`, a screenshot, or a tiny move when validating capability.
- Prefer a simple loop: capture -> inspect -> small action -> verify.
- Prefer command-line or API control when available; use desktop input when GUI control is actually needed.
