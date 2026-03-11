"""Cycle manager: advances stage and returns a subgoal for this tick.

Stages:
- evidence_table: propose building evidence table from semantic memory
- deep_dive: propose deep dive one strongest source; may request online search
- skill_build: propose creating a reusable workflow/plugin spec
- reflect: propose consolidate + cleanup

This plugin does not execute external actions.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


def run(topic: str = "longevity") -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    path = os.path.join(base_dir, "state_cycle.json")

    state: Dict[str, Any] = {
        "stage": 0,
        "stages": ["evidence_table", "deep_dive", "skill_build", "reflect"],
        "lastStageTs": 0,
    }
    try:
        if os.path.exists(path):
            state.update(json.load(open(path, "r", encoding="utf-8")))
    except Exception:
        pass

    stages: List[str] = list(state.get("stages") or ["evidence_table", "deep_dive", "skill_build", "reflect"])
    i = int(state.get("stage") or 0) % len(stages)
    stage = stages[i]

    # advance for next tick
    state["stage"] = (i + 1) % len(stages)
    state["lastStageTs"] = int(time.time())
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # create a subgoal packet
    if stage == "evidence_table":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "离线阶段：先把已沉淀的语义卡片整理成证据等级表，避免重复检索。",
            "next": "生成 evidence_table 草稿（人类RCT/观察/动物/体外；剂量/终点/风险/禁忌）。",
            "needs_network": False,
        }
    elif stage == "deep_dive":
        # Prefer feasibility: do as much as possible offline; only request network when truly blocked.
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "先在离线条件下最大化推进深挖（机制/剂量/人群/AE）；只有遇到关键缺口才请求联网。",
            "next": "选择最强来源并深挖；列出关键缺口；若缺口阻塞结论再发 search_request。",
            "needs_network": False,
            "feasibility_hint": "offline_first",
        }
    elif stage == "skill_build":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "把反复出现的整理/深挖步骤技能化，形成可复用 workflow/plugin 规格。",
            "next": "产出一个 skill spec（输入输出+测试骨架），写入 procedural 候选。",
            "needs_network": False,
        }
    else:
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "复盘本轮循环：去重、清理噪声、巩固语义记忆，并调整下一轮意图。",
            "next": "清理 outbox 噪声；总结 learning_queue；更新 intent。",
            "needs_network": False,
        }

    return {"ok": True, "stage": stage, "subgoal": subgoal, "state": state}
