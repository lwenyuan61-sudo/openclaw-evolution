"""Outbox cleaner: remove noisy 429/rate-limit records.

This is a maintenance skill to keep outbox and semantic memory clean.
- Filters candidates.jsonl lines where raw/search contains Exa free MCP rate limit / code 429.
- Creates a timestamped backup before rewrite.
- Resets outbox cursor to 0 (consumer should re-scan clean file).

Safety: only touches brainflow/outbox/*.jsonl and cursor.
"""

from __future__ import annotations

import os
import time
import shutil
import json
from typing import Any, Dict


def _is_rate_limit(obj: Dict[str, Any]) -> bool:
    s = " ".join([
        str(obj.get("raw", "")),
        str(obj.get("sources", "")),
        str(obj.get("search", "")),
    ]).lower()
    return (
        "rate limit" in s
        or "free mcp rate limit" in s
        or "code: 429" in s
        or "\"code\": 429" in s
        or "dashboard.exa.ai/api-keys" in s
        or "exaapikey" in s
    )


def run(also_clean_semantic: bool = True) -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    outbox_dir = os.path.join(base_dir, "outbox")
    cand = os.path.join(outbox_dir, "candidates.jsonl")
    cursor = os.path.join(outbox_dir, "cursor.txt")

    if not os.path.exists(cand):
        return {"ok": True, "skipped": True, "reason": "no candidates.jsonl"}

    ts = time.strftime("%Y%m%d-%H%M%S")
    backup = os.path.join(outbox_dir, f"candidates.jsonl.bak-{ts}")
    shutil.copy2(cand, backup)

    kept = 0
    dropped = 0
    tmp = cand + ".tmp"

    with open(cand, "r", encoding="utf-8", errors="replace") as rf, open(tmp, "w", encoding="utf-8") as wf:
        for ln in rf:
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except Exception:
                # keep unparsable lines
                wf.write(ln + "\n")
                kept += 1
                continue
            if _is_rate_limit(obj):
                dropped += 1
                continue
            wf.write(json.dumps(obj, ensure_ascii=False) + "\n")
            kept += 1

    os.replace(tmp, cand)

    # reset cursor so consumer doesn't miss after rewrite
    try:
        with open(cursor, "w", encoding="utf-8") as f:
            f.write("0\n")
    except Exception:
        pass

    # optional: semantic cleaner (best-effort)
    sem_cleaned = False
    if also_clean_semantic:
        sem_path = os.path.join(base_dir, "memory", "semantic", "cards.md")
        if os.path.exists(sem_path):
            with open(sem_path, "r", encoding="utf-8", errors="replace") as f:
                txt = f.read()
            # drop sections containing exa api-keys noise
            if "dashboard.exa.ai/api-keys" in txt.lower():
                # naive: remove lines containing those urls
                lines = [l for l in txt.splitlines() if "dashboard.exa.ai/api-keys" not in l.lower() and "exaapikey" not in l.lower()]
                with open(sem_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines) + "\n")
                sem_cleaned = True

    return {"ok": True, "backup": backup, "kept": kept, "dropped": dropped, "semantic_cleaned": sem_cleaned}
