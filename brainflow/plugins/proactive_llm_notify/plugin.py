"""proactive_llm_notify

After each cycle, ask LLM to judge whether there is a MAJOR breakthrough worth notifying the owner,
*based on concrete evidence* (file changes, new capabilities, scorecard, run packet).

Also supports a controlled "social ping" mechanism that increases with ticks,
but is still gated by LLM and quota timestamps to avoid spam.

If LLM says send=true, sends WhatsApp message via plugins.wa_send.

Safety:
- Requires concrete evidence; no vague "I have an idea".
- Rate-limits major notifications and social pings.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object
from plugins.wa_send.plugin import run as wa_send

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OWNER_PATH = os.path.join(BASE, "state_owner.json")
STATE_PATH = os.path.join(BASE, "state", "proactive_state.json")
RUN_PACKET = os.path.join(BASE, "state", "run_packet_latest.json")
SCORECARD = os.path.join(BASE, "memory", "procedural", "scorecard_latest.json")
STRATEGIES = os.path.join(BASE, "memory", "procedural", "strategies.json")
WORLD_MODEL = os.path.join(BASE, "state", "world_model.json")


def _load_json(path: str) -> Dict[str, Any]:
    try:
        if os.path.exists(path):
            obj = json.load(open(path, "r", encoding="utf-8"))
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return {}


def _save_state_patch(patch: Dict[str, Any]):
    st = _load_json(STATE_PATH)
    st.update(patch)
    try:
        os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def run(progress_scan: Dict[str, Any] | None = None, health: Dict[str, Any] | None = None, thinking: str = "minimal") -> Dict[str, Any]:
    # Subconscious rule: do NOT interrupt the main conversation unless explicitly enabled.
    # This prevents background loops from stealing attention from the owner.
    enabled = os.environ.get("BRAINFLOW_PROACTIVE_ENABLED", "0").strip().lower() in ("1", "true", "yes")
    if not enabled:
        return {"ok": True, "sent": False, "note": "proactive disabled (BRAINFLOW_PROACTIVE_ENABLED!=1)"}

    # Medium intensity (default): do not social-ping if owner was recently active.
    # This supports the 'human subconscious' feel: surface only when worth interrupting.
    mode = os.environ.get("BRAINFLOW_PROACTIVE_MODE", "medium").strip().lower() or "medium"

    owner = _load_json(OWNER_PATH)
    target = str(owner.get("whatsapp_target") or "").strip()
    if not target:
        return {"ok": False, "error": f"missing whatsapp_target in {OWNER_PATH}"}

    st = _load_json(STATE_PATH)
    ticks = int(st.get("ticks", 0) or 0)
    last_major = int(st.get("last_major_notify_ts", 0) or 0)
    last_social = int(st.get("last_social_ping_ts", 0) or 0)
    now = int(time.time())

    # Hard rate limits
    major_cooldown = 20 * 60  # 20 minutes
    social_cooldown = 60 * 60  # 1 hour

    can_major = (now - last_major) >= major_cooldown
    can_social = (now - last_social) >= social_cooldown

    # "Long time no message from owner" proxy: social_state mtime (written by 对话区) if available.
    last_owner = int(st.get("last_owner_interaction_ts", 0) or 0)
    owner_silent_sec = (now - last_owner) if last_owner else None

    # If the owner interacted recently, suppress social pings entirely in medium mode.
    if mode == "medium" and owner_silent_sec is not None and owner_silent_sec < 15 * 60:
        can_social = False

    # Self-heal: if health reports problems, apply deterministic fixes before deciding to notify.
    try:
        from plugins.queue_manager.plugin import trim_pending
        if isinstance(health, dict):
            issues = health.get("issues") if isinstance(health.get("issues"), list) else []
            for it in issues:
                if isinstance(it, dict) and it.get("kind") == "queue_bloat":
                    trim_pending(max_pending=250)
    except Exception:
        pass

    # If gateway seems down, attempt a cautious self-heal (restart) with cooldown.
    try:
        if isinstance(health, dict) and any((isinstance(it, dict) and it.get("kind") == "gateway_down") for it in (health.get("issues") or [])):
            # cooldown 30 minutes
            last_fix = int(st.get("last_gateway_fix_ts", 0) or 0)
            if now - last_fix >= 30 * 60:
                import subprocess
                OPENCLAW = r"C:\\Users\\15305\\AppData\\Roaming\\npm\\openclaw.cmd"
                subprocess.run([OPENCLAW, "gateway", "restart"], capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False, timeout=60)
                _save_state_patch({"last_gateway_fix_ts": now})
    except Exception:
        pass

    # Provide a small payload file to avoid long CLI args.
    payload_path = os.path.join(BASE, "memory", "procedural", "proactive_payload_latest.json")
    os.makedirs(os.path.dirname(payload_path), exist_ok=True)

    payload = {
        "schema": "brainflow.proactive_payload.v1",
        "t": now,
        "ticks": ticks,
        "can_major": can_major,
        "can_social": can_social,
        "owner_silent_sec": owner_silent_sec,
        "whatsapp_target": target,
        "progress_scan": progress_scan or {},
        "health": health or {},
        "paths": {
            "run_packet": RUN_PACKET,
            "scorecard": SCORECARD,
            "strategies": STRATEGIES,
            "world_model": WORLD_MODEL,
            "owner": OWNER_PATH,
            "proactive_state": STATE_PATH,
        },
        "definitions": {
            "major_progress": "A concrete breakthrough the system actually achieved, e.g. created/updated a plugin/workflow that adds capability, fixed a bug, improved reliability, or produced verified artifacts.",
            "not_major": "Vague ideas, unexecuted plans, speculative thoughts without proof.",
            "social_ping": "A short, low-stakes message driven by increasing desire-to-chat, but still should be rare and not spammy.",
        },
    }

    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    prompt = f"""Read local JSON payload file (JSON):
{payload_path}

Facts:
- WhatsApp gateway is already connected; do NOT ask to link/login/generate QR.
- Target number is payload.whatsapp_target.

You MUST read the files referenced in payload.paths if they exist.

Your job is ONLY to output STRICT JSON (no other text).

Fill this exact template:
{{
  \"schema\": \"brainflow.proactive_decision.v1\",
  \"t\": {now},
  \"send_major\": false,
  \"send_social\": false,
  \"major_title\": \"\",
  \"major_message\": \"\",
  \"major_evidence\": [],
  \"social_message\": \"\",
  \"rationale\": \"\"
}}

Decision rules:
- You already know the WhatsApp target as payload.whatsapp_target. Do NOT ask to link WhatsApp.
- MAJOR progress: ONLY if payload.can_major=true AND there is concrete evidence (file paths/changed artifacts) that the system actually built/fixed something.
- SOCIAL ping: ONLY if payload.can_social=true AND (owner_silent_sec is large) AND ticks is high enough AND message is rare.
- If you cannot cite evidence paths, keep send_major=false.
- social_message must be a gentle check-in, not a claim of factual emotions.
"""

    # Use a fresh session to avoid conversation drift into WhatsApp linking meta.
    r = oc_run(
        prompt,
        thinking=thinking,
        session_id="",
        timeout_sec=120,
        strict_json=True,
        expect_json=True,
        repair_attempts=1,
        agent_id="bf-llama",
    )
    if not r.get("ok"):
        # Heuristic fallback: only notify if there is concrete new capability evidence.
        decision = {"schema": "brainflow.proactive_decision.v1", "t": now, "send_major": False, "send_social": False}
        ch = (((progress_scan or {}).get("changes")) if isinstance(progress_scan, dict) else []) or []
        plugin_new = [c for c in ch if isinstance(c, dict) and str(c.get("path","")).startswith("plugins/") and c.get("kind") in ("new_file","modified_file")]
        # Major: any plugin/workflow change implies concrete capability work.
        if can_major and plugin_new:
            evid = [str(c.get("path")) for c in plugin_new[:8]]
            msg = "我检测到本轮有明确的能力/系统更新（涉及插件/工作流文件变更），可作为阶段性突破。\n" + "\n".join(["- " + e for e in evid])
            final = "主人，【重大进展】脑潮出现可验证的能力更新\n\n" + msg
            res = wa_send(target=target, message=final)
            _save_state_patch({"last_major_notify_ts": now})
            return {"ok": True, "sent": bool(res.get("ok")), "note": "LLM failed; heuristic major notify attempted", "evidence": evid, "send_results": [res], "llm": r}

        # Social: conservative fallback. Requires long owner silence + many ticks.
        silent_ok = (owner_silent_sec is not None and owner_silent_sec >= 6 * 3600)
        if can_social and silent_ok and ticks >= 200:
            final = "主人，我这边已经跑了一阵子还没等到你的新消息，想轻轻问一句：你现在最想让我优先推进哪件事？"
            res = wa_send(target=target, message=final)
            _save_state_patch({"last_social_ping_ts": now})
            return {"ok": True, "sent": bool(res.get("ok")), "note": "LLM failed; heuristic social ping attempted", "send_results": [res], "llm": r, "owner_silent_sec": owner_silent_sec}

        return {"ok": True, "sent": False, "note": "LLM call failed; no send", "llm": r}

    txt = (r.get("text") or "").strip()
    decision = r.get("json") if isinstance(r.get("json"), dict) else None

    # If model goes into WhatsApp-linking meta, treat as invalid.
    lowered = txt.lower()
    if any(k in lowered for k in ["qr", "qrcode", "login", "link whatsapp", "绑定", "二维码", "扫", "扫码"]):
        return {"ok": True, "sent": False, "note": "LLM drifted into WhatsApp linking meta; ignored", "llm_text": txt[-1200:], "payload_path": payload_path}

    err = None
    if decision is None:
        decision_obj, err = extract_first_json_object(txt)
        decision = decision_obj if isinstance(decision_obj, dict) else {}

    if not decision:
        # Repair pass: force JSON-only (fresh session reduces drift).
        repair_prompt = (
            "Convert the following into STRICT JSON ONLY for schema brainflow.proactive_decision.v1. "
            "Keep keys exactly: schema,t,send_major,send_social,major_title,major_message,major_evidence,social_message,rationale.\n\n"
            + txt[:2500]
        )
        rr = oc_run(
            repair_prompt,
            thinking=thinking,
            timeout_sec=60,
            session_id="",
            strict_json=True,
            expect_json=True,
            repair_attempts=1,
            agent_id="bf-llama",
        )
        if rr.get("ok"):
            decision2 = rr.get("json") if isinstance(rr.get("json"), dict) else None
            if decision2 is None:
                rtxt = (rr.get("text") or "").strip()
                decision2, _ = extract_first_json_object(rtxt)
            if isinstance(decision2, dict):
                decision = decision2
            else:
                rtxt = (rr.get("text") or "").strip()
                return {"ok": True, "sent": False, "note": f"LLM output not JSON (repair failed:{err})", "llm_text": txt[-800:], "repair_text": rtxt[-800:]}
        else:
            return {"ok": True, "sent": False, "note": f"LLM output not JSON (repair call failed:{err})", "llm_text": txt[-800:], "repair_llm": rr}

    sent_any = False
    results: List[Dict[str, Any]] = []

    # Normalize decision keys
    decision.setdefault("schema", "brainflow.proactive_decision.v1")
    decision.setdefault("send_major", False)
    decision.setdefault("send_social", False)
    decision.setdefault("major_title", "")
    decision.setdefault("major_message", "")
    decision.setdefault("major_evidence", [])
    decision.setdefault("social_message", "")
    decision.setdefault("rationale", "")

    if bool(decision.get("send_major")) and can_major:
        msg = str(decision.get("major_message") or "").strip()
        title = str(decision.get("major_title") or "").strip()
        if msg:
            final = f"主人，【重大进展】{title}\n\n{msg}" if title else f"主人，【重大进展】\n\n{msg}"
            results.append(wa_send(target=target, message=final))
            _save_state_patch({"last_major_notify_ts": now})
            sent_any = True

    if bool(decision.get("send_social")) and can_social:
        smsg = str(decision.get("social_message") or "").strip()
        if smsg:
            final = f"主人，{smsg}"
            results.append(wa_send(target=target, message=final))
            _save_state_patch({"last_social_ping_ts": now})
            sent_any = True

    return {"ok": True, "sent": sent_any, "decision": decision, "send_results": results, "payload_path": payload_path}
