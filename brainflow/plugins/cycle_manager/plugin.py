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
        "stages": [
            "stability_hardening",
            "capability_growth",
            "environment_adaptation",
            "evaluation_gate",
            "rollback_readiness",
            "reflect",
        ],
        "lastStageTs": 0,
    }
    try:
        if os.path.exists(path):
            state.update(json.load(open(path, "r", encoding="utf-8")))
    except Exception:
        pass

    stages: List[str] = list(state.get("stages") or [
        "stability_hardening",
        "capability_growth",
        "environment_adaptation",
        "evaluation_gate",
        "rollback_readiness",
        "reflect",
    ])
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
    if stage == "stability_hardening":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "稳定优先：压制空转与异常、降低重复失败，保障持续运行。",
            "next": "扫描失败类型/重复任务；提出降噪与去重措施；更新最小稳定策略。",
            "needs_network": False,
        }
    elif stage == "capability_growth":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "能力增长：提高拆解与执行质量，提升完成率与可复用度。",
            "next": "生成可复用技能/流程规格；完善输入输出与验证步骤。",
            "needs_network": False,
        }
    elif stage == "environment_adaptation":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "环境适应：根据资源与约束调整策略，离线优先，联网必要时再开。",
            "next": "基于当前 world_model/health 状态调整策略；标注何时需要联网。",
            "needs_network": False,
            "feasibility_hint": "offline_first",
        }
    elif stage == "evaluation_gate":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "评估门禁：每次变化都要可评估、可审计。",
            "next": "更新评估指标与阈值；生成最新 scorecard 并记录趋势。",
            "needs_network": False,
        }
    elif stage == "rollback_readiness":
        subgoal = {
            "kind": "subgoal",
            "stage": stage,
            "topic": topic,
            "why": "回滚准备：保证版本可恢复，失败自动回退。",
            "next": "检查最新备份；验证回滚路径可用；记录回滚演练结果。",
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
