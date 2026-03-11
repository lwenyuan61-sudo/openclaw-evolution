"""Batch executor: execute up to N leaf tasks per tick, with achievement checking + subtree pruning.

Owner requirements:
- Execute multiple most fine-grained subgoals per cycle (max 3 "parallel" -> we do sequential up to 3).
- Pick tasks by highest (value / feasibility) priority.
- After execution, check whether goals are achieved; if achieved, remove that goal and all descendants.
- If not achieved, keep (requeue) so next cycles can continue decomposing/executing.

This plugin orchestrates:
- queue_manager.pop / enqueue / mark_done / remove_subtree
- qinwan_execute.run(task) to do best-effort execution
- goal_check.run(cmd) for local command based verification

It only mutates brainflow state files (queue + goal tree) and writes an execution summary.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from plugins.queue_manager import plugin as qm
from plugins.qinwan_execute.plugin import run as qinwan_execute
from plugins.goal_check.plugin import run as goal_check
from plugins.candidate_write.plugin import run as cand_write


def _now() -> int:
    return int(time.time())


def _sleep_brief():
    time.sleep(0.05)


def _check_task_achieved(task: Dict[str, Any]) -> Dict[str, Any]:
    """Check achieved based on task.check.* fields.

    Supported schema:
      task["check"]["kind"] == "cmd"
      task["check_payload"] = {cmd, cwd, timeout_sec, expect_regex, expect_in}

    If no check provided, we default to achieved=False.
    """
    chk = task.get("check")
    payload = task.get("check_payload") or {}

    if isinstance(chk, dict) and str(chk.get("kind")) == "cmd":
        cmd = payload.get("cmd")
        if isinstance(cmd, list):
            return goal_check(
                cmd=cmd,
                cwd=payload.get("cwd"),
                timeout_sec=int(payload.get("timeout_sec") or 20),
                expect_regex=payload.get("expect_regex"),
                expect_in=str(payload.get("expect_in") or "stdout"),
            )

    return {"ok": True, "achieved": False, "reason": "no_check"}


def run(
    max_tasks: int = 3,
    time_budget_sec: int = 120,
    semantic_text: str = "",
) -> Dict[str, Any]:
    start = time.time()

    executed: List[Dict[str, Any]] = []
    pruned: List[str] = []
    requeued: List[str] = []

    # Execute up to max_tasks
    for _i in range(int(max_tasks)):
        if (time.time() - start) > float(time_budget_sec):
            break

        popr = qm.pop()
        task = popr.get("task") if isinstance(popr, dict) else None
        if not task:
            break

        # Execute (best-effort). This may also emit search_result to outbox (inside qinwan_execute).
        ex = qinwan_execute(task=task, semantic_text=semantic_text)

        # If execution produced new subgoals, enqueue them for subsequent cycles.
        try:
            # qinwan_execute returns either {mode:'offline', ...<task_executor keys>...}
            # or {mode:'offline+net', offline:{...}, net:{...}, search_result:{...}}
            base = ex or {}
            offline_part = base.get("offline") if isinstance(base.get("offline"), dict) else base

            new_sg = offline_part.get("new_subgoals")
            if isinstance(new_sg, list) and new_sg:
                qm.enqueue(children=new_sg)
        except Exception:
            pass

        # If execution produced a search_request (offline leaf needing network), emit it to outbox.
        try:
            base = ex or {}
            offline_part = base.get("offline") if isinstance(base.get("offline"), dict) else base
            sr = offline_part.get("search_request")
            if isinstance(sr, dict) and sr:
                cand_write(item=sr)
        except Exception:
            pass

        # Check achieved (task-level)
        ck = _check_task_achieved(task)

        # If achieved: prune subtree (task + descendants)
        if ck.get("achieved") is True:
            tid = str(task.get("id") or "")
            if tid:
                qm.remove_subtree(root_id=tid)
                pruned.append(tid)
        else:
            # Not achieved -> requeue (keep it for future cycles)
            # Add retry_count and gently decay priority to avoid infinite tight loops.
            try:
                rc = int(task.get("retry_count") or 0) + 1
            except Exception:
                rc = 1
            task["retry_count"] = rc
            try:
                task["priority"] = float(task.get("priority") or 0.5) * 0.97
            except Exception:
                pass
            qm.enqueue(children=[task])
            requeued.append(str(task.get("id") or ""))

        executed.append(
            {
                "task": task,
                "exec": ex,
                "check": ck,
                "t": _now(),
            }
        )

        _sleep_brief()

    return {
        "ok": True,
        "executed_n": len(executed),
        "executed": executed,
        "pruned": pruned,
        "requeued": requeued,
        "elapsed_sec": round(time.time() - start, 3),
    }
