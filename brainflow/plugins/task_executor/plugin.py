"""Execute one leaf subgoal into artifacts.

This is an MVP executor that produces tangible outputs under brainflow/memory/procedural.
If a task needs network, it emits a search_request to outbox (does not search itself).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


def _append(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def run(task: Dict[str, Any], semantic_text: str = "") -> Dict[str, Any]:
    if not isinstance(task, dict):
        return {"ok": True, "skipped": True, "reason": "no task"}

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(proc_dir, exist_ok=True)

    tid = str(task.get("id") or "")
    topic = str(task.get("topic") or "")
    stage = str(task.get("stage") or "")
    title = str(task.get("title") or "")
    nxt = str(task.get("next") or "")
    needs_net = bool(task.get("needs_network", False))

    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    # produce an artifact file per stage
    if stage == "evidence_table":
        path = os.path.join(proc_dir, "evidence_table.md")
        _append(path, f"\n## [{ts}] {title} ({tid})")
        _append(path, f"- next: {nxt}")
        _append(path, "- table: | Intervention | Evidence | Population | Dose | Endpoint | AE/Risk | Notes |")
        _append(path, "- table: |---|---|---|---|---|---|---|")
    elif stage == "deep_dive":
        path = os.path.join(proc_dir, "deep_dive.md")
        _append(path, f"\n## [{ts}] {title} ({tid})")
        _append(path, f"- next: {nxt}")
        _append(path, "- TODO: pick strongest source URL from semantic cards and summarize mechanism/dose/endpoint/AE")
    elif stage == "skill_build":
        path = os.path.join(proc_dir, "skill_specs.md")
        _append(path, f"\n## [{ts}] {title} ({tid})")
        _append(path, f"- next: {nxt}")
        _append(path, "- spec: input/output/tests skeleton (draft)")
    else:
        path = os.path.join(proc_dir, "reflect.md")
        _append(path, f"\n## [{ts}] {title} ({tid})")
        _append(path, f"- next: {nxt}")
        _append(path, "- note: reflect/cleanup pass")

    # Emit a search_request if needed
    search_req = None
    if needs_net:
        search_req = {
            "kind": "search_request",
            "topic": str(task.get("topic") or ""),
            "parent_id": str(task.get("parent_id") or ""),
            "task_id": tid,
            "query": f"{task.get('topic','')} {title} {nxt}".strip(),
            "why": "Leaf task marked needs_network; request dialogue zone to web search and write back results.",
        }

    # Infinite subgoals: generate deeper micro-subgoals based on current task + semantic memory.
    new_subgoals: List[Dict[str, Any]] = []
    try:
        import re
        urls = re.findall(r"https?://\S+", semantic_text or "")
        urls = [u.rstrip("').,]>") for u in urls][:10]

        if stage == "evidence_table" and urls:
            for u in urls[:5]:
                new_subgoals.append({
                    "kind": "subgoal",
                    "id": f"{tid}-{abs(hash(u))%100000}",
                    "parent_id": tid,
                    "topic": topic,
                    "stage": "evidence_table",
                    "title": "为单条来源补全表格字段",
                    "next": f"从来源提取：人群/剂量/终点/AE/禁忌；来源={u}",
                    "needs_network": False,
                })
        elif stage == "deep_dive" and urls:
            # break deep dive into sections
            for sec in ["机制", "剂量与给药方案", "主要终点", "不良事件/风险", "适用人群与禁忌"]:
                new_subgoals.append({
                    "kind": "subgoal",
                    "id": f"{tid}-{sec}",
                    "parent_id": tid,
                    "topic": topic,
                    "stage": "deep_dive",
                    "title": f"深挖章节：{sec}",
                    "next": f"基于最强来源整理该章节要点（必要时再触发 search_request）",
                    "needs_network": False,
                })
        elif stage == "skill_build":
            for sec in ["I/O schema", "测试用例", "沙盒验证计划"]:
                new_subgoals.append({
                    "kind": "subgoal",
                    "id": f"{tid}-{sec}",
                    "parent_id": tid,
                    "topic": topic,
                    "stage": "skill_build",
                    "title": f"技能构建：{sec}",
                    "next": "把该部分写成可复用的 spec 片段",
                    "needs_network": False,
                })
    except Exception:
        pass

    return {"ok": True, "artifact": path, "search_request": search_req, "new_subgoals": new_subgoals}
