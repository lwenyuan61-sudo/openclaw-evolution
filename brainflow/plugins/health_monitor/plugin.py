"""health_monitor

Lightweight runtime health checks for BrainFlow.

Detects:
- looping (ACC repeatCount)
- queue bloat (pending size)
- stale state_cycle.json
- WhatsApp gateway connectivity (best-effort via openclaw gateway status)

Returns a JSON object used by proactive_llm_notify for self-heal.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from typing import Any, Dict, List

OPENCLAW = r"C:\Users\15305\AppData\Roaming\npm\openclaw.cmd"


def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.exists(path):
            obj = json.load(open(path, "r", encoding="utf-8"))
            return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}
    return {}


def _repeat_count(acc: Dict[str, Any]) -> int:
    try:
        issues = acc.get("issues") if isinstance(acc.get("issues"), list) else []
        for it in issues:
            if isinstance(it, dict) and it.get("kind") == "repeating_payload":
                return int(it.get("repeatCount") or 0)
        st = acc.get("state") if isinstance(acc.get("state"), dict) else {}
        return int(st.get("repeatCount") or 0)
    except Exception:
        return 0


def _gateway_status() -> Dict[str, Any]:
    """Return gateway liveness + best-effort WhatsApp account string.

    Do NOT hard-require the exact phrase "WhatsApp gateway connected as" because formats differ.
    """
    try:
        p = subprocess.run([OPENCLAW, "gateway", "status"], capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, timeout=20)
        out = (p.stdout or "") + "\n" + (p.stderr or "")
        # Heuristics:
        alive = (p.returncode == 0) and ("Listening:" in out or "RPC probe: ok" in out or "Dashboard:" in out)
        # try extract any +number after 'connected' or 'as'
        m = re.search(r"connected\s+as\s+(\+\d+)", out, re.IGNORECASE)
        if not m:
            m = re.search(r"WhatsApp.*?(\+\d{6,})", out, re.IGNORECASE)
        return {
            "ok": p.returncode == 0,
            "alive": alive,
            "connected": None if not alive else (True if m else None),
            "as": (m.group(1) if m else None),
            "raw": out[-1200:],
        }
    except Exception as e:
        return {"ok": False, "alive": None, "connected": None, "error": str(e)}


def run() -> Dict[str, Any]:
    try:
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        now = int(time.time())

        acc = _load_json(os.path.join(base, "state_acc.json"))
        q = _load_json(os.path.join(base, "state_task_queue.json"))
        cyc_path = os.path.join(base, "state_cycle.json")

        repeat = _repeat_count(acc)
        pending_n = len(q.get("pending") or []) if isinstance(q.get("pending"), list) else 0

        cyc_mtime = int(os.stat(cyc_path).st_mtime) if os.path.exists(cyc_path) else 0
        cyc_age = now - cyc_mtime if cyc_mtime else None

        gw = _gateway_status()

        issues: List[Dict[str, Any]] = []
        if repeat >= 10:
            issues.append({"kind": "looping", "repeatCount": repeat})
        if pending_n >= 300:
            issues.append({"kind": "queue_bloat", "pending": pending_n})
        if cyc_age is not None and cyc_age >= 2 * 3600:
            issues.append({"kind": "cycle_stale", "age_sec": cyc_age})
        # Only flag WhatsApp disconnect if gateway is not alive; otherwise leave as unknown.
        if gw.get("alive") is False:
            issues.append({"kind": "gateway_down"})

        severity = 0
        for it in issues:
            if it.get("kind") in ("gateway_down",):
                severity = max(severity, 3)
            elif it.get("kind") in ("queue_bloat",):
                severity = max(severity, 2)
            elif it.get("kind") in ("looping", "cycle_stale"):
                severity = max(severity, 1)

        return {
            "ok": True,
            "t": now,
            "issues": issues,
            "severity": severity,
            "metrics": {"repeatCount": repeat, "pending": pending_n, "cycle_age_sec": cyc_age},
            "whatsapp": gw,
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
