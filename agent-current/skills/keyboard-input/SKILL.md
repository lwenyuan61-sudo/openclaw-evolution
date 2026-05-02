---
name: keyboard-input
description: Control Windows keyboard input via local Python Win32 calls. Use when the assistant needs to type text, press single keys, or send hotkeys like Ctrl+S, Alt+Tab, Enter, Esc, arrows, delete, and other simple keyboard interactions on this Windows machine.
---

# Keyboard Input

Use the bundled Python script for local Windows keyboard actions.

## Workflow

1. Prefer the smallest keyboard action first.
2. For risky shortcuts, narrate briefly before sending them.
3. Prefer text typing for plain input and hotkeys for control operations.
4. Keep sequences short and verifiable.

## Script

Run:

```powershell
python skills\keyboard-input\scripts\keyboard_input.py <action> [args]
```

## Actions

### Type text
```powershell
python skills\keyboard-input\scripts\keyboard_input.py type --text "hello"
```

### Press one key
```powershell
python skills\keyboard-input\scripts\keyboard_input.py key --name enter
python skills\keyboard-input\scripts\keyboard_input.py key --name esc
python skills\keyboard-input\scripts\keyboard_input.py key --name a
```

### Send hotkey
```powershell
python skills\keyboard-input\scripts\keyboard_input.py hotkey --keys ctrl,s
python skills\keyboard-input\scripts\keyboard_input.py hotkey --keys alt,tab
```

## Notes

- This skill is local Windows only.
- Use on the active foreground window.
- Prefer command/API control when available; use keyboard input when GUI control is actually needed.
