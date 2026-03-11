"""Goal manager bridge (front-end -> BrainFlow).

Reads a goal spec JSON and applies it to:
- GOAL.md (BRAINFLOW_GOAL source)
- state_control.json (topic + intent.topic)
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict


def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def run(goal_path: str = "memory/procedural/goal_manager.json", apply_goal_md: bool = True, apply_state_control: bool = True) -> Any:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    abs_goal = os.path.join(base_dir, goal_path.replace("/", os.sep))

    spec = _load_json(abs_goal)
    if not spec:
        return {"ok": False, "note": "goal_spec_missing_or_invalid", "path": abs_goal}

    goal_text = str(spec.get("goal_text") or "").strip()
    topic = str(spec.get("topic") or "").strip()
    intent_topic = str(spec.get("intent_topic") or "").strip() or topic

    updated = {}

    if apply_goal_md and goal_text:
        goal_md = os.path.join(base_dir, "GOAL.md")
        with open(goal_md, "w", encoding="utf-8") as f:
            f.write(goal_text)
        updated["goal_md"] = goal_md

    if apply_state_control and (topic or intent_topic):
        ctrl_path = os.path.join(base_dir, "state_control.json")
        ctrl = _load_json(ctrl_path) if os.path.exists(ctrl_path) else {}
        if topic:
            ctrl["topic"] = topic
        intent = ctrl.get("intent") if isinstance(ctrl.get("intent"), dict) else {}
        if intent_topic:
            intent["topic"] = intent_topic
        ctrl["intent"] = intent
        with open(ctrl_path, "w", encoding="utf-8") as f:
            json.dump(ctrl, f, ensure_ascii=False, indent=2)
        updated["state_control"] = ctrl_path

    return {"ok": True, "path": abs_goal, "updated": updated, "spec": spec}
