"""Semantic consolidation - MVP.

Turns raw forage into a compact semantic card:
- title (best-effort)
- urls (top 5)
- one-line takeaway (heuristic)

Writes markdown to brainflow/memory/semantic/cards.md
"""

from __future__ import annotations

import os
import re
import time
from typing import Any, Dict, List


def run(raw: str, topic: str = "general") -> Dict[str, Any]:
    text = raw or ""

    # Skip known rate-limit/error payloads
    low = text.lower()
    if "rate limit" in low or "code: 429" in low or "dashboard.exa.ai/api-keys" in low:
        return {"ok": True, "skipped": True, "reason": "rate_limit_noise"}

    # Extract first Title line if present
    m = re.search(r"^Title:\s*(.+)$", text, re.M)
    title = m.group(1).strip() if m else f"Card-{int(time.time())}"

    urls = re.findall(r"https?://\S+", text)
    urls = [u.rstrip("').,]>") for u in urls]
    urls = urls[:5]

    takeaway = "发现了与目标相关的新线索；建议按证据等级整理并评估风险。"
    if re.search(r"randomi[sz]ed|\brct\b", text, re.I):
        takeaway = "包含随机/对照临床证据线索；值得优先做证据等级表与风险审查。"

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    sem_dir = os.path.join(base_dir, "memory", "semantic")
    os.makedirs(sem_dir, exist_ok=True)
    path = os.path.join(sem_dir, "cards.md")

    # dedup by urls signature
    import hashlib
    sig = hashlib.sha256(("|".join(urls) or title).encode("utf-8", "ignore")).hexdigest()[:16]
    sig_path = os.path.join(sem_dir, "dedup_semantic.json")
    sig_state = {"seen": []}
    try:
        if os.path.exists(sig_path):
            import json
            sig_state.update(json.load(open(sig_path, "r", encoding="utf-8")))
    except Exception:
        pass
    seen = set(sig_state.get("seen") or [])
    if sig in seen:
        return {"ok": True, "skipped": True, "title": title, "urls": urls, "takeaway": takeaway, "path": path, "sig": sig}

    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(path, "a", encoding="utf-8") as f:
        f.write(f"\n## [{ts}] {title}\n")
        f.write(f"- topic: {topic}\n")
        f.write(f"- takeaway: {takeaway}\n")
        f.write(f"- sig: {sig}\n")
        if urls:
            f.write("- sources:\n")
            for u in urls:
                f.write(f"  - {u}\n")

    seen.add(sig)
    sig_state["seen"] = list(seen)[-500:]
    try:
        import json
        with open(sig_path, "w", encoding="utf-8") as f:
            json.dump(sig_state, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return {"ok": True, "title": title, "urls": urls, "takeaway": takeaway, "path": path, "sig": sig}
