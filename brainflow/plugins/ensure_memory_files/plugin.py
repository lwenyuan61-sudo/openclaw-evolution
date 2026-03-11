"""Ensure common memory files exist to prevent ENOENT."""
from __future__ import annotations

import os
import time
from typing import Dict


def _touch(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write("")


def run() -> Dict[str, object]:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    ts = time.localtime()
    today = time.strftime("%Y-%m-%d", ts)
    yday = time.strftime("%Y-%m-%d", time.localtime(time.time() - 86400))

    # main workspace memory files
    _touch(os.path.join(base, "MEMORY.md"))
    _touch(os.path.join(base, "memory", f"{today}.md"))
    _touch(os.path.join(base, "memory", f"{yday}.md"))

    # side workspaces (workspace-bf-*)
    root = os.path.abspath(os.path.join(base, ".."))
    for name in os.listdir(root):
        if not name.startswith("workspace-bf-"):
            continue
        w = os.path.join(root, name)
        _touch(os.path.join(w, "MEMORY.md"))
        _touch(os.path.join(w, "memory", f"{today}.md"))
        _touch(os.path.join(w, "memory", f"{yday}.md"))

    return {"ok": True, "today": today, "yday": yday}
