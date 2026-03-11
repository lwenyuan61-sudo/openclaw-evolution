"""GPT-driven subgoal generator.

Asks OpenClaw agent to propose ONE next subgoal (JSON) under current constraints.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict

from plugins._json_extract import extract_first_json_object
from plugins.openclaw_agent.plugin import run as oc_run


def run(goal: str, topic: str, context: str = "", offline: bool = True) -> Dict[str, Any]:
    # IMPORTANT: Do NOT inline large context in the CLI args (Windows command line limit).
    # Instead, instruct the OpenClaw agent to read from known local files.

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    goal_path = os.path.join(base_dir, "GOAL.md")
    sem_path = os.path.join(base_dir, "memory", "semantic", "cards.md")
    wm_path = os.path.join(base_dir, "state", "world_model.json")
    strat_path = os.path.join(base_dir, "memory", "procedural", "strategies.json")

    prompt = f"""You are the DeepThinking module. Generate ONE next subgoal as strict JSON.

Constraints:
- Must be feasible and *executable* as a concrete task.
- stage must be one of: evidence_table | deep_dive | skill_build | reflect
- next must be written as a short, step-by-step actionable instruction (not vague).
- If offline={offline}, do NOT require web access; if web is required, set needs_network=true and explain why.
- Prefer high value and high feasibility.

Return JSON ONLY with keys:
kind (must be 'subgoal'), stage, topic, title, why, next, needs_network (true/false).

Core goal: read local file: {goal_path}
Semantic memory context: read local file: {sem_path}
World model (state estimation + constraints): read local file: {wm_path}
Strategies (playbooks/policies): read local file: {strat_path}

Topic: {topic}

(Do not request huge context. If you cannot read files, still propose a feasible offline subgoal.)
"""

    r = oc_run(prompt, thinking="minimal", agent_id="bf-codex")
    if not r.get("ok"):
        # Fallback: return a feasible offline-first reflect subgoal.
        subgoal = {
            "kind": "subgoal",
            "stage": "reflect",
            "topic": topic,
            "title": "离线复盘与巩固",
            "why": "GPT 调用失败时，先做离线可行的复盘/去重/巩固，避免空转。",
            "next": "清理 outbox 噪声；巩固 semantic cards；调整下一轮意图。",
            "needs_network": False,
        }
        return {"ok": True, "subgoal": subgoal, "raw_text": "", "fallback": True, "error": r}

    txt = (r.get("text") or "").strip()

    obj, err = extract_first_json_object(txt)
    if isinstance(obj, dict):
        return {"ok": True, "subgoal": obj, "raw_text": txt}

    # attempt a repair pass (small prompt)
    repair_prompt = (
        "Convert the following into STRICT JSON object with keys: "
        "kind, stage, topic, title, why, next, needs_network. Output JSON ONLY.\n\n"
        + txt[:1500]
    )
    rr = oc_run(repair_prompt, thinking="minimal", session_id="", agent_id="bf-codex")
    if rr.get("ok"):
        rtxt = (rr.get("text") or "").strip()
        obj2, _ = extract_first_json_object(rtxt)
        if isinstance(obj2, dict):
            return {"ok": True, "subgoal": obj2, "raw_text": txt, "repaired": True, "repair_raw": rtxt}

    # fallback if still not compliant
    subgoal = {
        "kind": "subgoal",
        "stage": "reflect",
        "topic": topic,
        "title": "离线复盘与巩固",
        "why": f"GPT 输出不符合 JSON 约束({err})时，先做离线可行的复盘/去重/巩固，避免空转。",
        "next": "清理 outbox 噪声；巩固 semantic cards；调整下一轮意图。",
        "needs_network": False,
    }
    return {"ok": True, "subgoal": subgoal, "raw_text": txt, "fallback": True, "note": "LLM JSON parse failed"}
