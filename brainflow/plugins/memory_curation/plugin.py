"""memory_curation

LLM-led memory/forgetting loop.

Inputs (file-based):
- episodic log tail
- trace tail
- scorecard/strategies/world_model

Outputs:
- memory/procedural/highlights.md (important breakthroughs)
- Upserts to TWO vector stores:
  - brainflow.sqlite (general)
  - brainflow_important.sqlite (important)

Forgetting policy:
- 'forget' items are not written to vector stores.
- Periodically prunes general store (low-importance old items).

All outputs are schema-aligned and robust to non-JSON LLM responses.
"""

from __future__ import annotations

import json
import os
import time
import hashlib
from typing import Any, Dict, List, Optional

from plugins.openclaw_agent.plugin import run as oc_run
from core.vector_store import LocalVectorStore


def _safe_read(path: str, max_chars: int = 8000) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
    except Exception:
        pass
    return ""


def _append(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text.rstrip() + "\n")


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    if not text:
        return None
    a = text.find("{")
    b = text.rfind("}")
    js = text[a : b + 1] if a != -1 and b != -1 and b > a else text
    try:
        obj = json.loads(js)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def run(run_id: str = "", trace_path: str = "", thinking: str = "minimal") -> Dict[str, Any]:
    base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc = os.path.join(base, "memory", "procedural")
    state = os.path.join(base, "state")
    os.makedirs(proc, exist_ok=True)

    # Resolve run_id/trace_path
    if not run_id or not trace_path:
        rp = _extract_json(_safe_read(os.path.join(state, "run_packet_latest.json"), 20000)) or {}
        eng = (rp.get("engine") or {}) if isinstance(rp, dict) else {}
        run_id = run_id or str(eng.get("run_id") or "")
        trace_path = trace_path or str(eng.get("trace") or "")

    episodic_path = os.path.join(base, "memory", "episodic", "idle.md")
    score_path = os.path.join(proc, "scorecard_latest.json")
    strat_path = os.path.join(proc, "strategies.json")
    wm_path = os.path.join(state, "world_model.json")

    episodic_tail = _safe_read(episodic_path, 12000)[-6000:]
    trace_tail = _safe_read(trace_path, 12000)[-6000:] if trace_path else ""
    score = _safe_read(score_path, 4000)
    strat = _safe_read(strat_path, 4000)
    wm = _safe_read(wm_path, 6000)

    payload_path = os.path.join(proc, "memory_curation_payload_latest.json")
    payload = {
        "schema": "brainflow.memory_curation_payload.v1",
        "t": int(time.time()),
        "run_id": run_id,
        "paths": {
            "episodic": episodic_path,
            "trace": trace_path,
            "scorecard": score_path,
            "strategies": strat_path,
            "world_model": wm_path,
        },
        "tails": {
            "episodic_tail": episodic_tail,
            "trace_tail": trace_tail,
        },
        "notes": {
            "definition_important": "Important = concrete breakthrough/capability change with evidence (file paths, artifacts, measurable improvements).",
            "definition_normal": "Normal = useful but not critical; keep in episodic, optionally store in general vector DB if it helps retrieval.",
            "definition_forget": "Forget = noise/repetition/meta-chat; do not store in vectors; do not create highlights.",
        },
    }
    with open(payload_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    prompt = f"""You are the Memory Curation module for BrainFlow.

Read local JSON payload:
{payload_path}

You MUST judge the value of the run's logs and outputs.

Output STRICT JSON ONLY with schema brainflow.memory_curation_decision.v1:
{{
  \"schema\": \"brainflow.memory_curation_decision.v1\",
  \"t\": <unix>,
  \"run_id\": \"{run_id}\",
  \"items\": [
    {{
      \"id\": \"...\",                 // stable id, e.g. 'run:<run_id>:highlight:1'
      \"category\": \"important|normal|forget\",
      \"importance\": 0.0,              // 0-10
      \"title\": \"...\",
      \"summary\": \"...\",
      \"evidence\": [\"file:path\", \"trace:...\"],
      \"store_general\": true,
      \"store_important\": false
    }}
  ],
  \"rationale\": \"...\"
}}

Rules:
- IMPORTANT must have evidence (file paths/artifacts). If none, do not mark important.
- For IMPORTANT: store_general=true and store_important=true.
- For NORMAL: store_general=true only if it will help retrieval later.
- FORGET: store_general=false and store_important=false.
- Keep items <= 5.
"""

    # Use a fresh session to avoid drift.
    r = oc_run(prompt, thinking=thinking, session_id="", timeout_sec=120, agent_id="bf-qwen")
    txt = (r.get("text") or "").strip() if isinstance(r, dict) else ""
    decision = _extract_json(txt)

    if not isinstance(decision, dict):
        # Repair attempt
        rr = oc_run(
            "Convert the following into STRICT JSON only for schema brainflow.memory_curation_decision.v1.\n\n" + txt[:2500],
            thinking=thinking,
            session_id="",
            timeout_sec=60,
            agent_id="bf-qwen",
        )
        decision = _extract_json((rr.get("text") or "").strip()) if rr.get("ok") else None

    if not isinstance(decision, dict):
        decision = {
            "schema": "brainflow.memory_curation_decision.v1",
            "t": int(time.time()),
            "run_id": run_id,
            "items": [],
            "rationale": "LLM decision not available; no curation applied.",
        }

    items = decision.get("items") if isinstance(decision.get("items"), list) else []

    # Setup vector stores (two DBs)
    vs_general = LocalVectorStore(
        db_path=os.path.join(base, "memory", "vector_store", "brainflow.sqlite"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.environ.get("BRAINFLOW_EMBED_MODEL", "nomic-embed-text"),
    )
    vs_important = LocalVectorStore(
        db_path=os.path.join(base, "memory", "vector_store", "brainflow_important.sqlite"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.environ.get("BRAINFLOW_EMBED_MODEL", "nomic-embed-text"),
    )

    highlights_path = os.path.join(proc, "highlights.md")

    stored = {"general": 0, "important": 0}
    highlights_written = 0

    for it in items[:5]:
        if not isinstance(it, dict):
            continue
        cat = str(it.get("category") or "").strip()
        imp = float(it.get("importance") or 0.0)
        title = str(it.get("title") or "").strip()
        summary = str(it.get("summary") or "").strip()
        evidence = it.get("evidence") if isinstance(it.get("evidence"), list) else []
        store_general = bool(it.get("store_general"))
        store_important = bool(it.get("store_important"))

        # Enforce policy
        if cat == "important":
            if not evidence:
                cat = "normal"
                store_important = False
            else:
                store_general = True
                store_important = True

        if cat == "forget":
            store_general = False
            store_important = False

        doc_id = str(it.get("id") or "").strip()
        if not doc_id:
            h = hashlib.sha256((run_id + title + summary).encode("utf-8", "ignore")).hexdigest()[:16]
            doc_id = f"run:{run_id}:{cat}:{h}"

        doc = {
            "schema": "brainflow.memory_item.v1",
            "run_id": run_id,
            "category": cat,
            "importance": imp,
            "title": title,
            "summary": summary,
            "evidence": evidence,
            "paths": {"episodic": episodic_path, "trace": trace_path},
        }
        doc_text = json.dumps(doc, ensure_ascii=False)

        if store_general:
            try:
                vs_general.upsert(
                    doc_id=f"mem:{doc_id}",
                    text=doc_text,
                    meta={"category": cat, "run_id": run_id, "title": title},
                    doc_type="memory_item",
                    importance=imp,
                    ts=int(time.time()),
                )
                stored["general"] += 1
            except Exception:
                pass

        if store_important:
            try:
                vs_important.upsert(
                    doc_id=f"mem:{doc_id}",
                    text=doc_text,
                    meta={"category": cat, "run_id": run_id, "title": title},
                    doc_type="memory_item",
                    importance=max(imp, 8.0),
                    ts=int(time.time()),
                )
                stored["important"] += 1
            except Exception:
                pass

        if cat == "important" and title and summary:
            highlights_written += 1
            _append(
                highlights_path,
                f"\n## [{time.strftime('%Y-%m-%d %H:%M:%S')}] {title}\n- run: {run_id}\n- importance: {imp}\n- summary: {summary}\n- evidence:\n" + "\n".join(["  - " + str(e) for e in evidence]),
            )

    # Forgetting/prune: do it cheaply every ~50 ticks if we have proactive_state
    pruned = None
    try:
        pst = _extract_json(_safe_read(os.path.join(state, "proactive_state.json"), 8000)) or {}
        ticks = int(pst.get("ticks", 0) or 0)
        if ticks % 50 == 0:
            pruned = vs_general.prune(keep_newest=5000, min_importance_keep=6.0, max_age_seconds=30 * 24 * 3600)
    except Exception:
        pass

    return {
        "ok": True,
        "payload_path": payload_path,
        "decision": decision,
        "stored": stored,
        "highlights_written": highlights_written,
        "pruned": pruned,
    }
