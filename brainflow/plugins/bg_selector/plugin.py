"""BG Selector (candidate action scoring).

Upgraded behavior:
- If BRAINFLOW_LLM_JUDGES=1, ask OpenClaw agent (QinWan) to propose ranked actions.
- Otherwise fall back to heuristic scoring.

This module does NOT execute; it only suggests.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

from plugins.openclaw_agent.plugin import run as oc_run


def score_candidate(text: str) -> Dict[str, Any]:
    t = (text or "").lower()
    score = 0.0
    reasons: List[str] = []

    def hit(pat: str, w: float, why: str):
        nonlocal score
        if re.search(pat, t):
            score += w
            reasons.append(f"+{w} {why}")

    hit(r"randomi[sz]ed|rct\b", 4, "RCT")
    hit(r"double[- ]blind|placebo", 2.5, "blinded/placebo")
    hit(r"systematic review|meta[- ]analysis", 2.0, "review/meta")
    hit(r"phase\s*(ii|2|iii|3)\b|nct\d+", 2.0, "trial registry/phase")

    hit(r"rapamycin|sirolimus|m\s*tor\b|mtor", 1.5, "mTOR")
    hit(r"senolytic|senescence", 1.5, "senolytics")
    hit(r"partial reprogramming|oskm|yamanaka", 1.5, "reprogramming")
    hit(r"epigenetic clock|methylation", 1.0, "epigenetic clocks")

    hit(r"2026|2025", 0.5, "recent year")

    score = min(score, 10.0)
    return {"score": score, "reasons": reasons}


def _heuristic(raw: str, top_k: int = 3) -> Dict[str, Any]:
    s = score_candidate(raw)
    score = float(s["score"])

    actions = [
        {
            "kind": "action_candidate",
            "action": "make_evidence_table",
            "priority": score,
            "why": s["reasons"],
            "prompt": "把线索整理成证据等级表（人类RCT/观察/动物/体外），并列风险与可行动版本。",
        },
        {
            "kind": "action_candidate",
            "action": "deep_dive_one",
            "priority": max(0.0, score - 1.0),
            "why": s["reasons"],
            "prompt": "选择其中一条最强证据线索，做机制/剂量/风险/适用人群/禁忌的深挖。",
        },
        {
            "kind": "action_candidate",
            "action": "update_semantic_cards",
            "priority": max(0.0, score - 2.0),
            "why": s["reasons"],
            "prompt": "把本次发现沉淀为语义卡片（带来源链接与一句话结论）。",
        },
    ]

    actions = sorted(actions, key=lambda x: x["priority"], reverse=True)[: int(top_k)]
    return {"ok": True, "score": score, "reasons": s["reasons"], "actions": actions, "mode": "heuristic"}


def run(raw: str, top_k: int = 3, topic: str = "", goal_text: str = "") -> Dict[str, Any]:
    use_llm = os.environ.get("BRAINFLOW_LLM_JUDGES", "0").strip().lower() in ("1", "true", "yes")
    if not use_llm:
        return _heuristic(raw, top_k=top_k)

    prompt = f"""You are QinWan (亲碗). Propose high-value actions for BrainFlow based on context.

Hard constraints:
- Highest priority: owner's (李文远) benefit and system safety.
- Output STRICT JSON only.

Return schema:
{{
  "ok": true,
  "actions": [
     {{"stage": "...", "priority": 0..10, "why": ["..."], "success_criteria": "..."}}
  ]
}}

Topic: {topic}
Goal constitution:
{goal_text[:1500]}

Context:
{(raw or '')[:5000]}
"""

    r = oc_run(
        prompt,
        thinking="minimal",
        session_id="bf-bg",
        timeout_sec=90,
        strict_json=True,
        expect_json=True,
        repair_attempts=1,
        agent_id="bf-codex",
    )
    if not r.get("ok"):
        out = _heuristic(raw, top_k=top_k)
        out["llm_error"] = r
        return out

    obj = r.get("json") if isinstance(r.get("json"), dict) else None
    if obj is None:
        txt = (r.get("text") or "").strip()
        s = txt.find("{")
        e = txt.rfind("}")
        js = txt[s : e + 1] if (s != -1 and e != -1 and e > s) else txt
        try:
            obj = json.loads(js)
        except Exception:
            obj = None

    if isinstance(obj, dict):
        acts = obj.get("actions")
        if isinstance(acts, list):
            acts = acts[: int(top_k)]
        return {"ok": True, "actions": acts or [], "mode": "llm"}

    return _heuristic(raw, top_k=top_k)
