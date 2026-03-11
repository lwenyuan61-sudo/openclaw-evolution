"""Front queue bridge: front-end commitments -> BrainFlow tasks.

Reads memory/procedural/front_queue.jsonl, dedups by id, emits to outbox/candidates.jsonl
and writes memory/procedural/front_outbox.jsonl acknowledgements.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List


def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _write_json(path: str, obj: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def _append_jsonl(path: str, rows: List[Dict[str, Any]]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run() -> Dict[str, Any]:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    q_path = os.path.join(base, "memory", "procedural", "front_queue.jsonl")
    state_path = os.path.join(base, "memory", "procedural", "front_queue_state.json")
    outbox_path = os.path.join(base, "outbox", "candidates.jsonl")
    ack_path = os.path.join(base, "memory", "procedural", "front_outbox.jsonl")

    if not os.path.exists(q_path):
        return {"ok": True, "note": "no_queue"}

    state = _load_json(state_path)
    seen = set(state.get("seen_ids") or [])

    new_items = []
    acks = []
    with open(q_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            rid = str(obj.get("id") or obj.get("task_id") or "")
            if not rid:
                rid = f"front-{hash(line)}"
                obj["id"] = rid
            if rid in seen:
                continue
            seen.add(rid)
            new_items.append(obj)
            acks.append({"t": int(time.time()), "id": rid, "status": "queued"})

    if new_items:
        _append_jsonl(outbox_path, new_items)
        _append_jsonl(ack_path, acks)

    _write_json(state_path, {"seen_ids": list(seen)[-2000:]})
    return {"ok": True, "queued": len(new_items), "ack": len(acks)}
