"""Queue manager for hierarchical subgoals.

Owner policy upgrades:
- Prioritize tasks by (value / feasibility) ratio (approx), not just feasibility.
- Support subtree pruning: if a goal is achieved, remove that goal and all descendants.
- Persist a simple goal tree index to enable descendant lookup.

Functions:
- enqueue(children[]): append tasks if not already pending/done
- pop(): pop one pending task
- mark_done(task_id)
- remove_subtree(root_id): remove from pending and mark done for root + descendants
- trim_pending(max_pending=200): drop lowest-priority tail to cap backlog

State files:
- brainflow/state_task_queue.json
- brainflow/state_goal_tree.json
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Set


def _base_dir() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def _queue_path() -> str:
    return os.path.join(_base_dir(), "state_task_queue.json")


def _tree_path() -> str:
    return os.path.join(_base_dir(), "state_goal_tree.json")


def _load(path: str) -> Dict[str, Any]:
    st = {"pending": [], "done": [], "max_done": 2000, "seen": {}, "max_seen": 5000, "max_pending": 500}
    try:
        if os.path.exists(path):
            st.update(json.load(open(path, "r", encoding="utf-8")))
    except Exception:
        pass
    st["pending"] = list(st.get("pending") or [])
    st["done"] = list(st.get("done") or [])
    if not isinstance(st.get("seen"), dict):
        st["seen"] = {}
    st["max_seen"] = int(st.get("max_seen") or 5000)
    st["max_pending"] = int(st.get("max_pending") or 500)
    return st


def _save(path: str, st: Dict[str, Any]):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_tree() -> Dict[str, Any]:
    st = {"nodes": {}, "updated_at": int(time.time())}
    p = _tree_path()
    try:
        if os.path.exists(p):
            st.update(json.load(open(p, "r", encoding="utf-8")))
    except Exception:
        pass
    if not isinstance(st.get("nodes"), dict):
        st["nodes"] = {}
    return st


def _save_tree(st: Dict[str, Any]):
    st["updated_at"] = int(time.time())
    _save(_tree_path(), st)


def _register_node(tree: Dict[str, Any], task: Dict[str, Any]):
    tid = str(task.get("id") or "").strip()
    if not tid:
        return
    nodes: Dict[str, Any] = tree["nodes"]
    if tid in nodes:
        return
    nodes[tid] = {
        "id": tid,
        "parent_id": str(task.get("parent_id") or ""),
        "topic": str(task.get("topic") or ""),
        "stage": str(task.get("stage") or task.get("kind") or ""),
        "title": str(task.get("title") or ""),
        "t_created": int(task.get("t_created") or int(time.time())),
    }


def enqueue(children: List[Dict[str, Any]]) -> Dict[str, Any]:
    path = _queue_path()
    st = _load(path)

    pending = st["pending"]
    done = set(st["done"])
    pending_ids = set(t.get("id") for t in pending if isinstance(t, dict))

    # pruning threshold (non-core tasks)
    min_priority = float(os.environ.get("BRAINFLOW_MIN_PRIORITY", "0.2"))

    tree = _load_tree()

    def calc_priority(task: Dict[str, Any]) -> float:
        # If already has priority, use it
        try:
            if "priority" in task:
                return float(task.get("priority") or 0.0)
        except Exception:
            pass

        # Prefer (value / feasibility) as requested.
        v = None
        f = None
        try:
            vv = task.get("value")
            if isinstance(vv, dict) and "score" in vv:
                v = float(vv.get("score") or 0.0)
            elif isinstance(vv, (int, float)):
                v = float(vv)
        except Exception:
            v = None
        try:
            feas = task.get("feasibility")
            if isinstance(feas, dict) and "FeasibilityScore" in feas:
                f = float(feas.get("FeasibilityScore") or 0.0)
            elif isinstance(feas, (int, float)):
                f = float(feas)
        except Exception:
            f = None

        if v is None:
            v = 1.0
        if f is None:
            f = 3.0

        # avoid divide-by-zero; clamp
        f = max(0.5, min(10.0, f))
        v = max(0.0, min(10.0, v))

        # ratio + small feasibility penalty to avoid pathological low-feas tasks
        pr = (v / f) + (0.05 * f)
        return float(pr)

    import hashlib

    def content_sig(task: Dict[str, Any]) -> str:
        s = "|".join([
            str(task.get("topic") or ""),
            str(task.get("stage") or task.get("kind") or ""),
            str(task.get("title") or ""),
            str(task.get("next") or ""),
        ])
        return hashlib.sha256(s.encode("utf-8", "ignore")).hexdigest()[:16]

    # expire seen entries older than 24h
    now = int(time.time())
    seen: Dict[str, Any] = st.get("seen") or {}
    try:
        for k, v in list(seen.items()):
            if int(v or 0) < now - 24 * 3600:
                seen.pop(k, None)
    except Exception:
        pass

    added = 0
    dropped = 0
    for ch in children or []:
        if not isinstance(ch, dict):
            continue
        cid = ch.get("id")
        if not cid:
            continue
        if cid in done or cid in pending_ids:
            continue

        sig = content_sig(ch)
        if sig in seen:
            dropped += 1
            continue

        pr = calc_priority(ch)
        # Additional down-weight for repetitive reflect chores.
        try:
            if str(ch.get("stage") or "") == "reflect":
                pr *= 0.5
        except Exception:
            pass

        if pr < min_priority:
            dropped += 1
            continue

        _register_node(tree, ch)
        rec = {**ch, "priority": pr, "t_enqueued": now, "sig": sig}
        pending.append(rec)
        pending_ids.add(cid)
        seen[sig] = now
        added += 1

    # clamp seen size
    max_seen = int(st.get("max_seen") or 5000)
    if len(seen) > max_seen:
        # drop oldest
        items = sorted(seen.items(), key=lambda kv: int(kv[1] or 0), reverse=True)[:max_seen]
        st["seen"] = {k: v for k, v in items}
    else:
        st["seen"] = seen

    # Keep pending sorted by priority desc
    try:
        pending.sort(key=lambda x: float(x.get("priority", 0.0)), reverse=True)
    except Exception:
        pass

    # Hard cap pending size: drop lowest priority tail.
    max_pending = int(st.get("max_pending") or 500)
    if len(pending) > max_pending:
        pending[:] = pending[:max_pending]

    _save(path, st)
    _save_tree(tree)
    return {"ok": True, "added": added, "dropped": dropped, "pending": len(pending), "done": len(done)}


def pop() -> Dict[str, Any]:
    path = _queue_path()
    st = _load(path)

    pending = st["pending"]
    if not pending:
        return {"ok": True, "task": None, "pending": 0}

    task = pending.pop(0)
    _save(path, st)
    return {"ok": True, "task": task, "pending": len(pending)}


def mark_done(task_id: str) -> Dict[str, Any]:
    path = _queue_path()
    st = _load(path)

    done = list(st.get("done") or [])
    if task_id and task_id not in done:
        done.append(task_id)
    max_done = int(st.get("max_done") or 2000)
    if len(done) > max_done:
        done = done[-max_done:]
    st["done"] = done
    _save(path, st)
    return {"ok": True, "done": len(done)}


def _descendants(tree_nodes: Dict[str, Any], root_id: str) -> Set[str]:
    # build parent->children map on the fly
    kids: Dict[str, List[str]] = {}
    for nid, rec in (tree_nodes or {}).items():
        pid = str((rec or {}).get("parent_id") or "")
        if not pid:
            continue
        kids.setdefault(pid, []).append(str(nid))

    out: Set[str] = set()
    stack = [root_id]
    while stack:
        cur = stack.pop()
        if cur in out:
            continue
        out.add(cur)
        for ch in kids.get(cur, []):
            if ch not in out:
                stack.append(ch)
    return out


def trim_pending(max_pending: int = 200) -> Dict[str, Any]:
    """Cap backlog by dropping lowest priority tasks.

    This is a safety valve against queue bloat.
    """
    path = _queue_path()
    st = _load(path)
    pending0 = list(st.get("pending") or [])
    pending = pending0
    try:
        pending.sort(key=lambda x: float((x or {}).get("priority", 0.0)), reverse=True)
    except Exception:
        pass
    max_pending = int(max_pending)
    if max_pending < 1:
        max_pending = 1
    pending = pending[:max_pending]
    st["pending"] = pending
    _save(path, st)
    return {"ok": True, "before": len(pending0), "after": len(pending), "dropped": len(pending0) - len(pending)}


def remove_subtree(root_id: str) -> Dict[str, Any]:
    """Remove a goal and all its descendants.

    - Removes matching ids from pending list.
    - Adds all ids to done list.

    Note: This is best-effort; tasks not yet generated cannot be removed.
    """
    root_id = str(root_id or "").strip()
    if not root_id:
        return {"ok": False, "error": "root_id required"}

    qpath = _queue_path()
    st = _load(qpath)

    tree = _load_tree()
    nodes = tree.get("nodes") or {}
    ids = _descendants(nodes, root_id)

    # prune pending
    pending0 = st.get("pending") or []
    pending = [t for t in pending0 if not (isinstance(t, dict) and str(t.get("id")) in ids)]
    st["pending"] = pending

    # mark done
    done = list(st.get("done") or [])
    done_set = set(done)
    for tid in ids:
        if tid and tid not in done_set:
            done.append(tid)
            done_set.add(tid)

    st["done"] = done[-int(st.get("max_done") or 2000) :]
    _save(qpath, st)

    return {"ok": True, "root_id": root_id, "removed_pending": len(pending0) - len(pending), "marked_done": len(ids)}
