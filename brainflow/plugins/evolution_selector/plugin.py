"""Evolution selector (v0).

Creates a versioned candidate snapshot from latest self_rewrite proposal, and selects
best candidate based on latest scorecard (placeholder env-eval).
"""
from __future__ import annotations

import json
import os
import shutil
import time
from typing import Any, Dict


def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def run(base_dir: str | None = None) -> Any:
    base_dir = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    evo_dir = os.path.join(base_dir, "evolution")
    os.makedirs(evo_dir, exist_ok=True)
    cand_dir = os.path.join(evo_dir, "candidates")
    os.makedirs(cand_dir, exist_ok=True)
    sel_dir = os.path.join(evo_dir, "selected")
    os.makedirs(sel_dir, exist_ok=True)

    # Find latest applied proposal
    applied_dir = os.path.join(base_dir, "self_rewrite", "applied")
    latest = None
    latest_ts = 0.0
    if os.path.isdir(applied_dir):
        for name in os.listdir(applied_dir):
            p = os.path.join(applied_dir, name)
            if os.path.isdir(p):
                ts = os.path.getmtime(p)
                if ts > latest_ts:
                    latest_ts = ts
                    latest = p

    if not latest:
        return {"ok": False, "note": "no_applied_proposals"}

    # Create candidate snapshot folder
    cand_id = time.strftime("cand-%Y%m%d-%H%M%S")
    out = os.path.join(cand_dir, cand_id)
    os.makedirs(out, exist_ok=True)

    # Copy change_set + edits if exist
    for fn in ("change_set.json", "edits.json", "proposal.md", "result.json"):
        src = os.path.join(latest, fn)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(out, fn))

    # Attach scorecard (proxy for env eval in v0)
    score_path = os.path.join(base_dir, "memory", "procedural", "scorecard_latest.json")
    score = _load_json(score_path)
    if score:
        with open(os.path.join(out, "scorecard.json"), "w", encoding="utf-8") as f:
            json.dump(score, f, ensure_ascii=False, indent=2)

    # Selection: choose highest overall_score among candidates
    best = None
    best_score = -1
    for name in os.listdir(cand_dir):
        p = os.path.join(cand_dir, name)
        sc = _load_json(os.path.join(p, "scorecard.json"))
        s = int(sc.get("overall_score") or 0)
        if s > best_score:
            best_score = s
            best = p

    if best:
        sel_id = time.strftime("sel-%Y%m%d-%H%M%S")
        sel_path = os.path.join(sel_dir, sel_id)
        shutil.copytree(best, sel_path, dirs_exist_ok=True)
        return {"ok": True, "candidate": out, "selected": sel_path, "best_score": best_score}

    return {"ok": True, "candidate": out, "selected": None}
