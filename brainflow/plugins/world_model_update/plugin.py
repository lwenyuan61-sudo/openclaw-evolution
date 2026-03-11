"""World model + state estimation (LLM-led).

Writes a compact, actionable world model to state/world_model.json.
The world model is intended to be read by other LLM-driven plugins by file path,
so we do not have to inline it into prompts (Windows CLI length limits).

Design goals:
- be stable (schema + defaults)
- be auditable (include sources + timestamp)
- be actionable (constraints, resources, risks, next_best_actions)

This is an MVP.

Note: OpenClaw agent cannot read local files by path. To avoid prompt bloat and role drift,
we keep this module mostly deterministic: load the last world_model.json (if any), refresh timestamp,
and preserve owner-approved risk_posture (self_modify/external_actions).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional



DEFAULT_WORLD_MODEL: Dict[str, Any] = {
    "schema": "brainflow.world_model.v1",
    "t": 0,
    "owner_intent": {
        "priority": "fulfill_owner_needs",
        "style": "direct",
        "constraints": [
            "safety",
            "auditable",
            "reversible",
            "conversation_first",
        ],
        "ordering": [
            "fulfill_owner_needs",
            "stability_and_recoverability",
            "self_upgrade",
        ],
        "notes": "Priority order is owner-specified. 'stability' means service continuity and recoverability only; it must not become power-seeking.",
    },
    "environment": {
        "platform": "windows",
        "network": {"allowed": False, "reason": "offline loop; external search delegated to QinWan/OpenClaw"},
        "whatsapp_gateway": {"connected": None},
    },
    "resources": {"time_budget_sec": 180, "max_tasks_per_tick": 3},
    "risk_posture": {
        "self_modify": {"enabled": False, "allowlist": ["workflows/*.yaml", "memory/procedural/*.json", "VALUE_SYSTEM.md", "POLICY.md"]},
        "external_actions": {"enabled": False, "allowlist": []},
    },
    "state": {
        "topic": None,
        "drive": None,
        "query": None,
        "loop_risk": {"repeat_count": None, "signal": None},
    },
    "performance": {
        "last_scorecard": None,
        "trend": None,
        "bottlenecks": [],
    },
    "next_best_actions": [],
    "sources": [],
}


def _safe_read(path: str, max_chars: int = 8000) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
    except Exception:
        pass
    return ""


def run(thinking: str = "minimal") -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    state_dir = os.path.join(base_dir, "state")
    os.makedirs(state_dir, exist_ok=True)

    out_path = os.path.join(state_dir, "world_model.json")
    now = int(time.time())

    # Load previous world model if present.
    prev: Dict[str, Any] = {}
    try:
        if os.path.exists(out_path):
            with open(out_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                prev = obj
    except Exception:
        prev = {}

    wm: Dict[str, Any] = dict(DEFAULT_WORLD_MODEL)

    # Merge selected stable fields from prev.
    for k in ["owner_intent", "environment", "resources", "risk_posture", "state", "performance"]:
        if isinstance(prev.get(k), dict):
            wm[k] = prev[k]

    # Owner-approved policies live in procedural/strategies.json; prefer them.
    strat_path = os.path.join(base_dir, "memory", "procedural", "strategies.json")
    try:
        if os.path.exists(strat_path):
            strat = json.load(open(strat_path, "r", encoding="utf-8"))
        else:
            strat = {}
    except Exception:
        strat = {}

    pol = (strat.get("policies") or {}) if isinstance(strat, dict) else {}
    sm = pol.get("self_modify") if isinstance(pol, dict) else None
    ea = pol.get("external_actions") if isinstance(pol, dict) else None

    if isinstance(sm, dict):
        wm.setdefault("risk_posture", {})
        wm["risk_posture"].setdefault("self_modify", {})
        wm["risk_posture"]["self_modify"]["enabled"] = bool(sm.get("enabled"))
        if isinstance(sm.get("allowlist"), list):
            wm["risk_posture"]["self_modify"]["allowlist"] = sm.get("allowlist")

    if isinstance(ea, dict):
        wm.setdefault("risk_posture", {})
        wm["risk_posture"].setdefault("external_actions", {})
        wm["risk_posture"]["external_actions"]["enabled"] = bool(ea.get("enabled"))
        if isinstance(ea.get("allowlist"), list):
            wm["risk_posture"]["external_actions"]["allowlist"] = ea.get("allowlist")

    wm["schema"] = "brainflow.world_model.v1"
    wm["t"] = now

    # Ensure required structure exists.
    wm.setdefault("risk_posture", DEFAULT_WORLD_MODEL["risk_posture"])
    wm.setdefault("performance", DEFAULT_WORLD_MODEL["performance"])
    wm.setdefault("sources", [])
    wm["sources"] = list(dict.fromkeys((wm.get("sources") or []) + ["world_model_update_deterministic"]))

    tmp_path = out_path + ".tmp"
    tmp_path = out_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(wm, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, out_path)

    return {"ok": True, "path": out_path, "world_model": wm, "llm": {"ok": False, "error": "deterministic"}}
