"""ACC Monitor (conflict / anomaly / anti-loop) - MVP.

Checks a raw text for:
- repeated identical payloads
- too-short / empty payload
- suspicious self-loop markers

Persists lightweight state in brainflow/state_acc.json
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from typing import Any, Dict


def run(raw: str, min_chars: int = 200) -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    state_path = os.path.join(base_dir, "state_acc.json")

    text = raw or ""
    h = hashlib.sha256(text.encode("utf-8", "ignore")).hexdigest()[:16]

    state: Dict[str, Any] = {"lastHash": "", "repeatCount": 0, "lastTs": 0}
    try:
        if os.path.exists(state_path):
            state.update(json.load(open(state_path, "r", encoding="utf-8")))
    except Exception:
        pass

    repeat = h == (state.get("lastHash") or "")
    if repeat:
        state["repeatCount"] = int(state.get("repeatCount") or 0) + 1
    else:
        state["repeatCount"] = 0

    state["lastHash"] = h
    state["lastTs"] = int(time.time())

    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    issues = []
    if len(text.strip()) < int(min_chars):
        issues.append({"kind": "too_short", "len": len(text.strip())})
    if state["repeatCount"] >= 2:
        issues.append({"kind": "repeating_payload", "repeatCount": state["repeatCount"]})
    if "[bf" in text.lower() and "deepthink" in text.lower():
        issues.append({"kind": "possible_self_loop_marker"})

    ok = len(issues) == 0
    return {"ok": ok, "hash": h, "issues": issues, "state": state}
