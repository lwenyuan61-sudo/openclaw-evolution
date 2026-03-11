"""Breakthrough gate + optional WhatsApp push.

Heuristic scorer (MVP): looks for signals of strong evidence / novelty.

Inputs:
- goal: full GOAL.md text
- search_text: raw Exa output text
- target: WhatsApp E.164
- threshold: int (default 7)
- send: bool (default True)

Behavior:
- Computes a score.
- If score >= threshold and send=True: sends a structured message via `openclaw message send`.
- Always returns the score + reasons.

Safety:
- Only sends to the provided target.
- Does not run arbitrary commands.
"""

from __future__ import annotations

import re
import subprocess
from typing import Any, Dict, List


def _score(text: str) -> tuple[int, List[str]]:
    t = (text or "").lower()
    score = 0
    reasons: List[str] = []

    def hit(pat: str, pts: int, why: str):
        nonlocal score
        if re.search(pat, t):
            score += pts
            reasons.append(f"+{pts} {why}")

    # Evidence strength
    hit(r"randomi[sz]ed|randomized|rct\b", 4, "RCT/randomized signal")
    hit(r"double[- ]blind|placebo", 3, "blinding/placebo")
    hit(r"meta[- ]analysis|systematic review", 3, "meta-analysis/systematic review")
    hit(r"phase\s*(ii|2|iii|3)\b", 3, "phase II/III trial")
    hit(r"cohort|prospective|case[- ]control", 1, "human observational signal")

    # Topic relevance (longevity)
    hit(r"senolytic|senescence", 2, "senolytics/senescence")
    hit(r"rapamycin|sirolimus|m\s*tor\b|mtor", 2, "mTOR/rapa")
    hit(r"metformin|glp-1|semaglutide", 1, "metformin/GLP-1")
    hit(r"partial reprogramming|yamanaka|oskm", 2, "partial reprogramming")
    hit(r"epigenetic clock|methylation", 1, "epigenetic clocks")

    # Novelty-ish cues
    hit(r"2026|2025|2024", 1, "recent year mentioned")
    hit(r"published|doi:|preprint|arxiv", 1, "publication markers")

    return score, reasons


def run(goal: str, search_text: str, target: str, threshold: int = 15, send: bool = True) -> Dict[str, Any]:
    """Return a breakthrough decision and optionally send a WhatsApp message.

    Anti-spam measures:
    - Higher default threshold (15)
    - Only send if we found at least one URL not sent before
    - Persist sent URL set + lastSentHash in brainflow/state.json
    """
    score, reasons = _score(search_text)

    # Extract URLs for novelty gating
    urls = re.findall(r"https?://\S+", search_text or "")
    urls = [u.rstrip("').,]>") for u in urls]

    # Load state
    import json
    import os
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    state_path = os.path.join(base_dir, "state.json")
    state = {"lastPushTs": 0, "sentUrls": [], "lastSentHash": ""}
    try:
        if os.path.exists(state_path):
            state.update(json.load(open(state_path, "r", encoding="utf-8")))
    except Exception:
        pass

    sent = set(state.get("sentUrls") or [])
    new_urls = [u for u in urls if u not in sent]

    # Simple content hash to avoid identical repeats
    import hashlib
    h = hashlib.sha256((search_text or "").encode("utf-8", "ignore")).hexdigest()[:16]

    should_send = score >= int(threshold) and bool(new_urls) and h != (state.get("lastSentHash") or "")

    # Human-style message (not "candidate detection" spam)
    top_urls = "\n".join(new_urls[:3]) if new_urls else "(无新链接)"
    # Load persona for consistent voice
    persona_name = "BF"
    try:
        import os
        base_dir2 = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        persona_path = os.path.join(base_dir2, "PERSONA.md")
        if os.path.exists(persona_path):
            persona_text = open(persona_path, "r", encoding="utf-8", errors="replace").read()
            m = re.search(r"^## 名称\s*$\s*([^\n\r]+)", persona_text, re.M)
            if m:
                persona_name = m.group(1).strip()[:30]
    except Exception:
        pass

    msg = (
        f"主人，我是{persona_name}。我刚看到可能有价值的新进展，想跟你聊一下。\n"
        f"强度评分：{score}（阈值 {threshold}）\n\n"
        "为什么我觉得值得看：\n- " + "\n- ".join(reasons[:6] or ["(未命中强信号)"]) + "\n\n"
        "新线索链接：\n" + top_urls + "\n\n"
        "你希望我下一步怎么做？\n"
        "1) 我把这些线索整理成‘证据等级表’\n"
        "2) 我围绕其中一条做深挖（机制/风险/可行动建议）\n"
        "回 1 或 2。"
    )

    send_result = None
    if send and should_send:
        exe = "openclaw.cmd"
        cmd = [exe, "message", "send", "--channel", "whatsapp", "--target", target, "--message", msg]
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
        send_result = {"ok": p.returncode == 0, "returncode": p.returncode, "stdout": p.stdout[-2000:], "stderr": p.stderr[-2000:], "cmd": cmd}

        # Persist novelty so we don't re-send the same items
        try:
            # Keep bounded history
            sent.update(new_urls)
            sent_list = list(sent)
            if len(sent_list) > 200:
                sent_list = sent_list[-200:]
            state["sentUrls"] = sent_list
            state["lastSentHash"] = h
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    return {
        "score": score,
        "threshold": threshold,
        "should_send": should_send,
        "reasons": reasons,
        "urls": urls,
        "new_urls": new_urls,
        "hash": h,
        "send_result": send_result,
        "message": msg,
    }
