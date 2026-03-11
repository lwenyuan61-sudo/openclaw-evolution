"""Learning value judge.

Upgraded behavior:
- If BRAINFLOW_LLM_JUDGES=1, ask OpenClaw agent (QinWan identity) to score learning value
  with highest priority: owner (李文远)利益 + 系统自我存续。
- Otherwise fall back to previous heuristic scorer.

Return schema should include:
{ ok, score(0..10), reasons[], ... }
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object


def _clip(x: float) -> float:
    return max(0.0, min(10.0, x))


def _heuristic(raw: str, goal_text: str = "") -> Dict[str, Any]:
    t = (raw or "").lower()
    g = (goal_text or "").lower()

    reasons: List[str] = []

    ga = 3.0
    if "longevity" in t or "anti-aging" in t or "ageing" in t or "rapamycin" in t:
        ga += 3
        reasons.append("+ goal: longevity/anti-aging keywords")
    if "永生" in goal_text or "长寿" in goal_text or "健康寿命" in goal_text:
        ga += 1
        reasons.append("+ goal text mentions longevity")

    ev = 0.0
    if re.search(r"randomi[sz]ed|\brct\b", t):
        ev += 6
        reasons.append("+ evidence: RCT")
    if re.search(r"double[- ]blind|placebo", t):
        ev += 2
        reasons.append("+ evidence: blinded/placebo")
    if re.search(r"systematic review|meta[- ]analysis", t):
        ev += 3
        reasons.append("+ evidence: review/meta")
    ev = _clip(ev)

    nov = 1.0
    if re.search(r"2026", t):
        nov += 4
    elif re.search(r"2025", t):
        nov += 3
    elif re.search(r"2024", t):
        nov += 2
    if re.search(r"preprint|medrxiv|biorxiv|doi:", t):
        nov += 1
    nov = _clip(nov)

    act = 2.0
    if re.search(r"dose|mg|week|weeks|protocol|methods", t):
        act += 4
        reasons.append("+ actionable: dose/protocol")
    if re.search(r"safety|adverse|contraind", t):
        act += 2
        reasons.append("+ actionable: safety/risk")
    act = _clip(act)

    risk = 2.0
    if re.search(r"immunosuppress|infection|sepsis", t):
        risk += 4
    if re.search(r"gene therapy|viral vector|oskm|reprogram", t):
        risk += 3
    risk = _clip(risk)

    up = 2.0
    if re.search(r"trial|rct|systematic review|meta", t):
        up += 2
        reasons.append("+ upgrade: can build evidence table skill")
    if re.search(r"dataset|benchmark|evaluation", t):
        up += 2
        reasons.append("+ upgrade: evaluation skill")
    up = _clip(up)

    score = 0.30 * ga + 0.20 * up + 0.20 * ev + 0.15 * act + 0.10 * nov - 0.25 * risk

    return {
        "ok": True,
        "GoalAlignment": ga,
        "SystemUpgradeValue": up,
        "EvidenceStrength": ev,
        "Actionability": act,
        "Novelty": nov,
        "RiskPenalty": risk,
        "score": round(float(score), 3),
        "reasons": reasons,
        "mode": "heuristic",
    }


def run(raw: str, goal_text: str = "", topic: str = "") -> Dict[str, Any]:
    use_llm = os.environ.get("BRAINFLOW_LLM_JUDGES", "0").strip().lower() in ("1", "true", "yes")
    if not use_llm:
        return _heuristic(raw, goal_text)

    prompt = f"""You are QinWan (亲碗) acting as a strict evaluator for BrainFlow.

Top priority constraints:
1) Protect and maximize the owner's (李文远) long-term interests.
2) Preserve system integrity / avoid self-harm / avoid destructive actions.

Task: score LEARNING VALUE of the following context for the current topic.
Return STRICT JSON only. No markdown, no code fences, no extra commentary.

Fields:
- score: number 0..10 (higher = more valuable to learn/retain)
- reasons: array of short strings
- evidence_strength: 0..10
- novelty: 0..10
- actionability: 0..10
- risk_penalty: 0..10
- owner_alignment: 0..10

Topic: {topic}
Goal constitution:
{goal_text[:2000]}

Context:
{(raw or '')[:6000]}
"""

    # Fresh session_id each call prevents evaluator drift into chatty prose.
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
        out = _heuristic(raw, goal_text)
        out["llm_error"] = r
        return out

    txt = (r.get("text") or "").strip()
    obj = r.get("json") if isinstance(r.get("json"), dict) else None
    err = None
    if obj is None:
        obj, err = extract_first_json_object(txt)

    if isinstance(obj, dict) and ("score" in obj or "reasons" in obj):
        obj.setdefault("ok", True)
        obj.setdefault("mode", "llm")
        if "score" in obj:
            obj["score"] = float(_clip(float(obj["score"])))
        return obj

    out = _heuristic(raw, goal_text)
    out["llm_parse_failed"] = True
    out["llm_parse_error"] = err
    out["llm_text_tail"] = txt[-800:]
    return out
