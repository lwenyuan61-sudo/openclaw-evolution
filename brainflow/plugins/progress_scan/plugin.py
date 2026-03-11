"""progress_scan

Detects concrete progress signals from the local BrainFlow workspace.

Outputs:
- changes: list of notable file changes/new files
- tick_state: counters used for social/proactive scheduling

This is deliberately local/heuristic; final decision is made by an LLM judge.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Tuple

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STATE_PATH = os.path.join(BASE, "state", "proactive_state.json")

WATCH_DIRS = [
    os.path.join(BASE, "plugins"),
    os.path.join(BASE, "workflows"),
    os.path.join(BASE, "memory", "procedural"),
]

# Owner interaction proxy: if 表意识/对话区 writes social state, treat that as "owner contact".
SOCIAL_STATE = os.path.join(BASE, "state_social.json")

WATCH_EXT = {".py", ".yaml", ".yml", ".json", ".md"}


def _load_state() -> Dict[str, Any]:
    try:
        if os.path.exists(STATE_PATH):
            return json.load(open(STATE_PATH, "r", encoding="utf-8"))
    except Exception:
        pass
    return {
        "schema": "brainflow.proactive_state.v1",
        "ticks": 0,
        "last_scan_ts": 0,
        "files": {},
        "last_major_notify_ts": 0,
        "last_social_ping_ts": 0,
    }


def _save_state(st: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _iter_files() -> List[str]:
    out: List[str] = []
    for d in WATCH_DIRS:
        if not os.path.exists(d):
            continue
        for root, _dirs, files in os.walk(d):
            for fn in files:
                ext = os.path.splitext(fn)[1].lower()
                if ext not in WATCH_EXT:
                    continue
                p = os.path.join(root, fn)
                out.append(p)
    return out


def _rel(p: str) -> str:
    try:
        return os.path.relpath(p, BASE).replace("\\", "/")
    except Exception:
        return p


def run(max_changes: int = 30) -> Dict[str, Any]:
    st = _load_state()
    now = int(time.time())

    prev = st.get("files") if isinstance(st.get("files"), dict) else {}
    cur: Dict[str, Dict[str, Any]] = {}

    changes: List[Dict[str, Any]] = []

    for p in _iter_files():
        try:
            stat = os.stat(p)
            rel = _rel(p)
            cur[rel] = {"mtime": int(stat.st_mtime), "size": int(stat.st_size)}

            before = prev.get(rel)
            if before is None:
                changes.append({"kind": "new_file", "path": rel, "mtime": int(stat.st_mtime), "size": int(stat.st_size)})
            else:
                if int(before.get("mtime", 0)) != int(stat.st_mtime) or int(before.get("size", -1)) != int(stat.st_size):
                    changes.append({
                        "kind": "modified_file",
                        "path": rel,
                        "mtime": int(stat.st_mtime),
                        "size": int(stat.st_size),
                        "before": before,
                    })
        except Exception:
            continue

    # prune: keep most recent
    changes.sort(key=lambda x: int(x.get("mtime", 0)), reverse=True)
    changes = changes[: max_changes]

    # Track last owner interaction by mtime of SOCIAL_STATE (best-effort).
    try:
        if os.path.exists(SOCIAL_STATE):
            st["last_owner_interaction_ts"] = int(os.stat(SOCIAL_STATE).st_mtime)
    except Exception:
        pass

    st["schema"] = "brainflow.proactive_state.v1"
    st["ticks"] = int(st.get("ticks", 0) or 0) + 1
    st["last_scan_ts"] = now
    st["files"] = cur

    _save_state(st)

    return {
        "ok": True,
        "now": now,
        "tick_state": {k: st.get(k) for k in ("ticks", "last_major_notify_ts", "last_social_ping_ts", "last_owner_interaction_ts")},
        "changes": changes,
        "state_path": _rel(STATE_PATH),
    }
