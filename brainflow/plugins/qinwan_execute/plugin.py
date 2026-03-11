"""QinWan executor bridge (L3).

Purpose
- BrainFlow must call QinWan to *execute* the next task every tick.
- This plugin is the bridge: it uses OpenClaw agent (same identity/model stack as QinWan)
  to perform networked steps when needed, and writes results back into BrainFlow artifacts.

Behavior
- If task.needs_network is False: fallback to local task_executor (pure offline artifacts).
- If task.needs_network is True: ask OpenClaw agent to do a web search + summarize into a short payload,
  then append into procedural artifacts, and emit a search_result to outbox.

Safety
- Irreversible actions are still guarded by GOAL.md policy (handled at higher layer).
- This plugin only writes into brainflow/memory and brainflow/outbox.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from plugins.openclaw_agent.plugin import run as oc_run
from plugins.task_executor.plugin import run as offline_exec
from plugins.semantic_consolidate.plugin import run as semantic_consolidate
from core.vector_store import LocalVectorStore


def _append(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(text + "\n")


def run(task: Dict[str, Any], semantic_text: str = "") -> Dict[str, Any]:
    if not isinstance(task, dict) or not task:
        return {"ok": True, "skipped": True, "reason": "no task"}

    # Always produce local artifacts (offline) first.
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(proc_dir, exist_ok=True)

    # Shared vector stores (dual DB):
    # - important DB is always consulted for retrieval
    # - general DB is consulted when it helps
    vs_general = LocalVectorStore(
        db_path=os.path.join(base_dir, "memory", "vector_store", "brainflow.sqlite"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.environ.get("BRAINFLOW_EMBED_MODEL", "nomic-embed-text"),
    )
    vs_important = LocalVectorStore(
        db_path=os.path.join(base_dir, "memory", "vector_store", "brainflow_important.sqlite"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.environ.get("BRAINFLOW_EMBED_MODEL", "nomic-embed-text"),
    )

    out = offline_exec(task=task, semantic_text=semantic_text)

    needs_net = bool(task.get("needs_network", False))
    if not needs_net:
        return {"ok": True, "mode": "offline", **out}

    # Networked assist (QinWan identity): ask OpenClaw agent to search + summarize.
    topic = str(task.get("topic", "") or "")
    title = str(task.get("title", "") or "")
    nxt = str(task.get("next", "") or "")
    query = str(task.get("query", "") or "").strip()
    if not query:
        query = f"{topic} {title} {nxt}".strip()

    # Retrieval (important always, general when useful)
    retrieved_imp = []
    retrieved_gen = []
    try:
        retrieved_imp = vs_important.search(query, top_k=4, min_importance=6.0)
    except Exception:
        retrieved_imp = []
    try:
        # Only consult general DB if we have few important hits.
        if len(retrieved_imp) < 2:
            retrieved_gen = vs_general.search(query, top_k=4, min_importance=4.0)
    except Exception:
        retrieved_gen = []

    def _pack_hits(hits):
        out = []
        for h in hits[:4]:
            if not isinstance(h, dict):
                continue
            txt = str(h.get("text") or "")
            if len(txt) > 800:
                txt = txt[:800] + "…"
            out.append({"id": h.get("id"), "importance": h.get("importance"), "score": h.get("score"), "text": txt})
        return out

    prompt = f"""You are QinWan (亲碗). Execute ONE networked task for BrainFlow.

Hard requirements:
- You MUST use your available web search/browsing tools to gather evidence.
- Prefer RCTs, systematic reviews, reputable institutions.
- Keep output compact, factual, and cite URLs.

Task JSON:
{json.dumps(task, ensure_ascii=False)[:2000]}

Goal constitution: read local file: {os.path.join(base_dir, 'GOAL.md')}
Semantic context: read local file: {os.path.join(base_dir, 'memory', 'semantic', 'cards.md')}

Important memory hits (ALWAYS consult):
{json.dumps(_pack_hits(retrieved_imp), ensure_ascii=False)[:2000]}

General memory hits (consult if helpful):
{json.dumps(_pack_hits(retrieved_gen), ensure_ascii=False)[:2000]}

Do:
1) Web search for the query and open/fetch at least 2 sources (if accessible) to confirm details.
2) Extract key fields needed to move the task forward (population/dose/endpoint/AE/contraindications/etc as relevant).
3) Provide a short, actionable conclusion.

Output STRICT JSON ONLY with keys:
- title (string)
- query (string)
- urls (array of strings, 3-8)
- evidence_level (string; e.g., RCT/systematic review/observational/preclinical/unknown)
- summary (string <= 1200 chars)
- extracted (object)
- risk_notes (string)
- next_steps (array of strings, 3-8)

Query: {query}
"""
    # Ask OpenClaw agent for STRICT JSON and enable a small repair loop if it returns prose.
    r = oc_run(
        prompt,
        thinking="minimal",
        session_id="qinwan-exec",
        timeout_sec=90,
        strict_json=True,
        expect_json=True,
        repair_attempts=1,
        agent_id="bf-codex",
    )

    # Always log what QinWan actually executed (command + stderr tail) for audit.
    try:
        logp = os.path.join(proc_dir, "qinwan_exec_log.md")
        _append(logp, f"\n## [{time.strftime('%Y-%m-%d %H:%M:%S')}] qinwan_execute\n- task: {json.dumps(task, ensure_ascii=False)}\n- cmd: {json.dumps(r.get('cmd', []), ensure_ascii=False)}\n- ok: {r.get('ok')}\n- stderr_tail: {(r.get('stderr') or '')[-800:]}\n- stdout_tail: {(r.get('stdout') or '')[-800:]}\n")
    except Exception:
        pass

    if not r.get("ok"):
        _append(os.path.join(proc_dir, "net_errors.md"), f"\n## [{time.strftime('%Y-%m-%d %H:%M:%S')}] network exec failed\n- task: {json.dumps(task, ensure_ascii=False)}\n- err: {r}")
        return {"ok": True, "mode": "offline+net_failed", "offline": out, "net": r}

    # Prefer parsed JSON from openclaw_agent (with repair). Fall back to manual parsing.
    obj = r.get("json") if isinstance(r.get("json"), dict) else None
    txt = (r.get("text") or "").strip()

    if obj is None:
        js = txt
        s = txt.find("{")
        e = txt.rfind("}")
        if s != -1 and e != -1 and e > s:
            js = txt[s : e + 1]

        try:
            obj = json.loads(js)
        except Exception:
            obj = {"query": query, "urls": [], "summary": txt[:1200], "extracted": {}, "risk_notes": "JSON parse failed"}

    # Append into procedural artifact
    p = out.get("artifact") or os.path.join(proc_dir, "network_results.md")
    _append(
        p,
        f"\n### [NET:{time.strftime('%Y-%m-%d %H:%M:%S')}] {obj.get('title') or title}"
        f"\n- query: {obj.get('query')}"
        f"\n- evidence_level: {obj.get('evidence_level','')}"
        f"\n- urls: {obj.get('urls')}"
        f"\n- summary: {obj.get('summary')}"
        f"\n- extracted: {json.dumps(obj.get('extracted') or {}, ensure_ascii=False)}"
        f"\n- next_steps: {json.dumps(obj.get('next_steps') or [], ensure_ascii=False)}"
        f"\n- risk: {obj.get('risk_notes','')}"
    )

    # 1) Write semantic memory card (markdown) and dedup by urls signature
    try:
        raw_for_sem = "\n".join(
            [
                f"Title: {obj.get('title') or title}",
                f"Evidence: {obj.get('evidence_level','')} ",
                f"Summary: {obj.get('summary','')}",
                "Sources:",
                *[str(u) for u in (obj.get('urls') or [])],
            ]
        )
        sem = semantic_consolidate(raw=raw_for_sem, topic=topic)
    except Exception:
        sem = {"ok": False}

    # 2) Upsert semantic chunk into vector store
    try:
        sem_text = json.dumps(
            {
                "topic": topic,
                "title": obj.get("title") or title,
                "query": obj.get("query") or query,
                "evidence_level": obj.get("evidence_level", ""),
                "urls": obj.get("urls", []),
                "summary": obj.get("summary", ""),
                "extracted": obj.get("extracted", {}),
                "next_steps": obj.get("next_steps", []),
                "risk_notes": obj.get("risk_notes", ""),
                "semantic_sig": sem.get("sig"),
            },
            ensure_ascii=False,
        )
        # semantic cards are important: write to BOTH vector DBs
        for _vs in (vs_general, vs_important):
            _vs.upsert(
                doc_id=f"sem:{sem.get('sig') or int(time.time())}",
                text=sem_text,
                meta={"topic": topic, "type": "semantic_card", "sig": sem.get("sig"), "urls": obj.get("urls", [])},
                doc_type="semantic_card",
                importance=8.0,
                ts=int(time.time()),
            )
    except Exception:
        pass

    # Emit a search_result item to outbox for downstream consolidation
    sr = {
        "kind": "search_result",
        "topic": topic,
        "task_id": str(task.get("id") or ""),
        "query": obj.get("query", query),
        "title": obj.get("title") or title,
        "evidence_level": obj.get("evidence_level", ""),
        "urls": obj.get("urls", []),
        "summary": obj.get("summary", ""),
        "extracted": obj.get("extracted", {}),
        "next_steps": obj.get("next_steps", []),
        "risk_notes": obj.get("risk_notes", ""),
        "semantic_sig": sem.get("sig"),
        "t": int(time.time()),
        "note": "由 qinwan_execute 调用 OpenClaw agent 联网执行并回写（已写入 semantic + vector store）。",
    }

    try:
        from plugins.candidate_write.plugin import run as cand_write

        cand_write(item=sr)
    except Exception:
        pass

    return {"ok": True, "mode": "offline+net", "offline": out, "net": obj, "semantic": sem, "search_result": sr}
