"""GPT-mediated web search via OpenClaw tools.

Asks OpenClaw agent to perform web_search/web_fetch and return a compact JSON result.
"""

from __future__ import annotations

from typing import Any, Dict

from plugins._json_extract import extract_first_json_object
from plugins.openclaw_agent.plugin import run as oc_run


def run(query: str, max_results: int = 5) -> Dict[str, Any]:
    prompt = f"""Use web_search to find up to {max_results} high-quality sources for the query.
Return JSON ONLY with keys: query, results (array of objects with title,url,snippet).
Query: {query}
"""
    r = oc_run(prompt, thinking="minimal", agent_id="bf-qwen")
    if not r.get("ok"):
        return r
    txt = (r.get("text") or "").strip()
    obj, err = extract_first_json_object(txt)
    if isinstance(obj, dict):
        return {"ok": True, "data": obj, "raw_text": txt}

    # Repair pass (fresh session to reduce drift)
    repair_prompt = (
        "Convert the following into STRICT JSON with keys: query, results (array of {title,url,snippet}). Output JSON ONLY.\n\n"
        + txt[:2000]
    )
    rr = oc_run(repair_prompt, thinking="minimal", session_id="", agent_id="bf-qwen")
    if rr.get("ok"):
        rtxt = (rr.get("text") or "").strip()
        obj2, _ = extract_first_json_object(rtxt)
        if isinstance(obj2, dict):
            return {"ok": True, "data": obj2, "raw_text": txt, "repaired": True, "repair_raw": rtxt}

    return {"ok": True, "data": None, "raw_text": txt, "note": f"LLM did not return strict JSON ({err})"}
