"""Feasibility judge.

Upgraded behavior:
- If BRAINFLOW_LLM_JUDGES=1, ask OpenClaw agent (QinWan) to score feasibility.
- Otherwise fall back to heuristic scorer.

Returns FeasibilityScore 0..10 and reasons/blockers.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object


def _clip(x: float) -> float:
    return max(0.0, min(10.0, x))


def _heuristic(task: Dict[str, Any]) -> Dict[str, Any]:
    offline = os.environ.get("BRAINFLOW_DISABLE_SEARCH", "").strip().lower() in ("1", "true", "yes")
    needs_net = str(task.get("needs_network", False)).lower() in ("true", "1", "yes")

    perm = 9.0
    reasons: List[str] = []
    if needs_net and offline:
        perm = 1.0
        reasons.append("needs_network but offline")
    elif needs_net:
        perm = 6.0
        reasons.append("needs_network")

    info = 7.0
    if needs_net and offline:
        info = 2.0

    res = 7.0

    txt = (str(task.get("title", "")) + " " + str(task.get("next", "")) + " " + str(task.get("why", "")))
    comp = 2.0
    if len(txt) > 400:
        comp = 5.0
    if len(txt) > 800:
        comp = 7.0

    feasibility = 0.35 * res + 0.30 * perm + 0.25 * info - 0.20 * comp
    feasibility = _clip(feasibility)

    return {
        "ok": True,
        "offline": offline,
        "needs_network": needs_net,
        "ResourceFit": _clip(res),
        "PermissionFit": _clip(perm),
        "InfoAvailability": _clip(info),
        "Complexity": _clip(comp),
        "FeasibilityScore": round(float(feasibility), 3),
        "reasons": reasons,
        "mode": "heuristic",
    }


def run(task: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(task, dict):
        return {"ok": False, "error": "task must be dict"}

    use_llm = os.environ.get("BRAINFLOW_LLM_JUDGES", "0").strip().lower() in ("1", "true", "yes")
    if not use_llm:
        return _heuristic(task)

    offline = os.environ.get("BRAINFLOW_DISABLE_SEARCH", "").strip().lower() in ("1", "true", "yes")

    prompt = f"""You are QinWan (亲碗). Score FEASIBILITY of executing this task in the current environment.

Hard constraints:
- Highest priority: owner's (李文远) benefit and system safety.
- If the task would violate safety or is destructive, feasibility must be very low and list blockers.
- Return STRICT JSON only. No markdown, no code fences, no extra keys beyond the schema, no trailing commentary.

Return fields:
- FeasibilityScore: 0..10
- blockers: array of strings
- assumptions: array of strings
- needs_network: boolean
- suggested_next: array of strings

Environment:
- offline_mode(BRAINFLOW_DISABLE_SEARCH)={offline}
- OS=Windows

Task JSON:
{json.dumps(task, ensure_ascii=False)[:2500]}
"""

    # Use a fresh session id each call to reduce "chat drift" (models start replying with prose).
    r = oc_run(
        prompt,
        thinking="minimal",
        session_id="",
        timeout_sec=90,
        strict_json=True,
        expect_json=True,
        repair_attempts=1,
        agent_id="bf-codex",
    )
    if not r.get("ok"):
        out = _heuristic(task)
        out["llm_error"] = r
        return out

    txt = (r.get("text") or "").strip()
    obj = r.get("json") if isinstance(r.get("json"), dict) else None
    err = None
    if obj is None:
        obj, err = extract_first_json_object(txt)

    if isinstance(obj, dict) and ("FeasibilityScore" in obj or "blockers" in obj or "suggested_next" in obj):
        if "FeasibilityScore" in obj:
            obj["FeasibilityScore"] = float(_clip(float(obj["FeasibilityScore"])))
        obj.setdefault("ok", True)
        obj.setdefault("mode", "llm")
        return obj

    out = _heuristic(task)
    out["llm_parse_failed"] = True
    out["llm_parse_error"] = err
    out["llm_text_tail"] = txt[-800:]
    return out
