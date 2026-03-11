"""Write a candidate item to brainflow/outbox/candidates.jsonl.

Brainflow should NOT message WhatsApp directly; it only emits candidates.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict


def _sanitize(obj: Any, *, max_str: int = 1200, max_list: int = 50, depth: int = 0) -> Any:
    """Make candidate payload safe for JSONL + small.

    - Truncates very long strings.
    - Bounds list lengths.
    - Recursively sanitizes dict/list.
    """
    if depth > 6:
        return "<depth_limit>"

    if obj is None:
        return None

    if isinstance(obj, (int, float, bool)):
        return obj

    if isinstance(obj, str):
        s = obj.replace("\r\n", "\n")
        # Strip extremely noisy OpenClaw / tool banners
        if "API rate limit" in s or "rate limit" in s:
            s = "<rate_limited>"
        if len(s) > max_str:
            s = s[: max_str - 20] + "...<truncated>"
        return s

    if isinstance(obj, list):
        xs = obj[:max_list]
        return [_sanitize(x, max_str=max_str, max_list=max_list, depth=depth + 1) for x in xs]

    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            # keys must be strings for stable JSON
            ks = str(k)
            out[ks] = _sanitize(v, max_str=max_str, max_list=max_list, depth=depth + 1)
        return out

    # Fallback: stringify unknown types
    return _sanitize(str(obj), max_str=max_str, max_list=max_list, depth=depth + 1)


def run(item: Dict[str, Any]) -> Dict[str, Any]:
    """Append a candidate item with dedup.

    Level-4 hardening:
    - Always write valid JSONL (one JSON object per line).
    - Sanitize oversized / noisy strings (e.g., tool stdout, rate-limit banners) so outbox never becomes un-parseable.
    - Keep records small and stable to prevent downstream CLI-length / parsing issues.

    Dedup strategy:
    - Compute a stable hash of the item (excluding `t`).
    - Maintain outbox/dedup_index.json containing recently seen hashes per kind.
    - If already seen, skip writing.

    Optional fields:
    - dedup_hash: if provided, used as the hash instead of computing from full item.
    """

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    outbox = os.path.join(base_dir, "outbox")
    os.makedirs(outbox, exist_ok=True)
    path = os.path.join(outbox, "candidates.jsonl")

    if not isinstance(item, dict):
        return {"ok": False, "error": "item must be dict"}

    item = _sanitize(item)
    kind = str(item.get("kind", "unknown"))

    # load dedup index
    index_path = os.path.join(outbox, "dedup_index.json")
    index = {"maxPerKind": 500, "seen": {}}  # seen[kind]=[hash...]
    try:
        if os.path.exists(index_path):
            index.update(json.load(open(index_path, "r", encoding="utf-8")))
    except Exception:
        pass

    seen = index.get("seen") or {}
    kind_list = list(seen.get(kind) or [])

    # compute hash
    import hashlib

    h = item.get("dedup_hash")
    if not h:
        payload = {k: v for k, v in item.items() if k != "t"}
        payload_s = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        h = hashlib.sha256(payload_s.encode("utf-8", "ignore")).hexdigest()[:16]

    if h in kind_list:
        return {"ok": True, "path": path, "skipped": True, "dedup_hash": h, "reason": "duplicate"}

    rec = {"t": int(time.time()), **item}

    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # persist dedup index (bounded)
    kind_list.append(h)
    max_per = int(index.get("maxPerKind") or 500)
    if len(kind_list) > max_per:
        kind_list = kind_list[-max_per:]
    seen[kind] = kind_list
    index["seen"] = seen
    try:
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {"ok": True, "path": path, "written": rec, "dedup_hash": h}
