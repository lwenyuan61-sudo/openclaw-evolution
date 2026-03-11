"""HTN-style subgoal decomposition.

Upgraded behavior:
- If BRAINFLOW_LLM_JUDGES=1, ask OpenClaw agent (QinWan) to decompose a subgoal into executable child tasks.
  Each child should be as fine-grained as possible and include a local command-based check when feasible.
- Otherwise fall back to the previous template-based decomposition.

Owner constraints:
- Highest priority: 李文远利益 + 系统自我存续/安全。
- Prefer checks runnable via local command (PowerShell) and non-destructive.

Returned child schema (recommended):
{
  id, parent_id, kind:"subgoal", title, next,
  needs_network:boolean,
  value:{score:0..10,...},
  feasibility:{FeasibilityScore:0..10,...},
  success_criteria:string,
  check:{kind:"cmd"},
  check_payload:{cmd:[...], timeout_sec:.., expect_regex:..}
}
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, List

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _template(subgoal: Dict[str, Any]) -> Dict[str, Any]:
    parent_id = str(subgoal.get("id") or _id())
    stage = str(subgoal.get("stage") or subgoal.get("kind") or "")
    topic = str(subgoal.get("topic") or "")

    subgoal = {**subgoal, "id": parent_id}

    children: List[Dict[str, Any]] = []

    def add(title: str, next_step: str, needs_network: bool = False):
        children.append(
            {
                "kind": "subgoal",
                "id": _id(),
                "parent_id": parent_id,
                "topic": topic,
                "stage": stage,
                "title": title,
                "next": next_step,
                "needs_network": needs_network,
                "t_created": int(time.time()),
            }
        )

    if stage == "evidence_table":
        add("抽取 sources 列表", "从 semantic cards 里抽取并去重 sources URL")
        add("证据等级字段设计", "定义列：证据等级/人群/剂量/终点/AE/禁忌/结论")
        add("生成表格草稿", "把已知信息填入表格草稿（未知留空，标记待搜索）")
    elif stage == "deep_dive":
        add("选最强来源", "按证据强度优先选择 RCT/系统综述来源")
        add("列出缺口清单", "列出缺失字段：剂量、样本量、主要终点、AE、纳排标准", needs_network=False)
        offline = os.environ.get("BRAINFLOW_DISABLE_SEARCH", "").strip().lower() in ("1", "true", "yes")
        if offline:
            add("记录待联网缺口", "把需要联网补齐的字段写成 blocked 条目，等待对话区后续联网回填", needs_network=False)
        else:
            add("发出搜索请求(若必要)", "若缺口影响结论，则生成 search_request 给对话区联网补齐", needs_network=True)
    elif stage == "skill_build":
        add("定义技能输入输出", "把反复任务抽象为函数/工作流的 I/O schema")
        add("生成测试用例", "至少 happy/edge 两类测试")
        add("写入 procedural 草案", "输出 skill spec，等待对话区批准后进入沙盒实现")
    else:
        add("清理噪声", "清理 outbox 中重复/错误条目")
        add("巩固语义记忆", "把本轮关键 takeaways 写入 semantic cards")
        add("调整下一轮意图", "根据主人反馈调整 drive/topic/query")

    return {"ok": True, "parent": subgoal, "children": children, "mode": "template"}


def run(subgoal: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(subgoal, dict):
        raise ValueError("subgoal must be dict")

    use_llm = os.environ.get("BRAINFLOW_LLM_JUDGES", "0").strip().lower() in ("1", "true", "yes")
    if not use_llm:
        return _template(subgoal)

    parent_id = str(subgoal.get("id") or _id())
    subgoal = {**subgoal, "id": parent_id}

    offline = os.environ.get("BRAINFLOW_DISABLE_SEARCH", "").strip().lower() in ("1", "true", "yes")

    prompt = f"""You are QinWan (亲碗). Decompose ONE parent subgoal into the most fine-grained executable child tasks.

Top priority constraints:
1) Owner 李文远利益最大化。
2) 系统自我存续/安全（禁止破坏性命令；禁止删除/格式化/关机等）。

Environment:
- OS=Windows
- offline_mode={offline}

Hard requirements:
- Return STRICT JSON only: {{"parent":..., "children":[...]}}.
- No markdown, no code fences, no trailing commentary.
- Each child must include:
  - id (string), parent_id (string), kind="subgoal"
  - title, next, needs_network
  - value: {{"score":0..10, "reasons":[...]}}
  - feasibility: {{"FeasibilityScore":0..10, "blockers":[...]}}
  - success_criteria (string)
  - check: {{"kind":"cmd"}}
  - check_payload: {{"cmd":[...], "timeout_sec": 20, "expect_regex": "..." (optional), "expect_in":"stdout"}}

- Prefer checks that are non-destructive PowerShell commands like:
  - Test-Path
  - Select-String
  - python -c (read-only)

Parent subgoal JSON:
{json.dumps(subgoal, ensure_ascii=False)[:3000]}
"""

    # Fresh session_id each call prevents decomposition drift into chatty prose.
    r = oc_run(
        prompt,
        thinking="minimal",
        session_id="",
        timeout_sec=120,
        strict_json=True,
        expect_json=True,
        repair_attempts=1,
        agent_id="bf-codex",
    )
    if not r.get("ok"):
        out = _template(subgoal)
        out["llm_error"] = r
        return out

    txt = (r.get("text") or "").strip()
    # Prefer parsed JSON extracted by openclaw_agent; fall back to manual extraction.
    obj = r.get("json") if isinstance(r.get("json"), dict) else None
    err = None
    if obj is None:
        obj, err = extract_first_json_object(txt)
    try:
        if not isinstance(obj, dict):
            raise ValueError(err or "no_json")
        parent = obj.get("parent") or subgoal
        children = obj.get("children")
        if not isinstance(children, list):
            children = []

        # normalize ids and parent links
        norm_children = []
        for ch in children:
            if not isinstance(ch, dict):
                continue
            ch = {**ch}
            ch.setdefault("kind", "subgoal")
            ch.setdefault("id", _id())
            ch["parent_id"] = parent_id
            ch.setdefault("t_created", int(time.time()))
            norm_children.append(ch)

        return {"ok": True, "parent": {**subgoal, **(parent if isinstance(parent, dict) else {})}, "children": norm_children, "mode": "llm"}
    except Exception:
        out = _template(subgoal)
        out["llm_parse_failed"] = True
        out["llm_parse_error"] = err
        out["llm_text_tail"] = txt[-800:]
        return out
