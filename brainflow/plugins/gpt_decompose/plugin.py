"""GPT-driven HTN decomposition.

Input: a parent subgoal
Output: list of child subgoals (JSON array)
"""

from __future__ import annotations

import json
from typing import Any, Dict

from plugins._json_extract import extract_first_json_array
from plugins.openclaw_agent.plugin import run as oc_run


def run(parent: Dict[str, Any], offline: bool = True) -> Dict[str, Any]:
    prompt = f"""Decompose the following parent subgoal into 3-6 child subgoals (JSON array). JSON ONLY.

Constraints:
- If offline={offline}, children should avoid web; if truly needed, set needs_network=true.
- Each child must include: kind='subgoal', id (string), parent_id, topic, stage, title, next, needs_network.

Parent subgoal JSON:
{json.dumps(parent, ensure_ascii=False)}
"""

    r = oc_run(prompt, thinking="minimal", agent_id="bf-codex")
    if not r.get("ok"):
        return r

    txt = (r.get("text") or "").strip()
    arr, err = extract_first_json_array(txt)
    if isinstance(arr, list):
        return {"ok": True, "children": arr, "raw_text": txt}

    # Repair pass
    repair_prompt = (
        "Convert the following into STRICT JSON ARRAY of child subgoals. Output JSON ONLY.\n\n"
        + txt[:2500]
    )
    rr = oc_run(repair_prompt, thinking="minimal", session_id="", agent_id="bf-codex")
    if rr.get("ok"):
        rtxt = (rr.get("text") or "").strip()
        arr2, _ = extract_first_json_array(rtxt)
        if isinstance(arr2, list):
            return {"ok": True, "children": arr2, "raw_text": txt, "repaired": True, "repair_raw": rtxt}

    return {"ok": True, "children": None, "raw_text": txt, "note": f"LLM did not return strict JSON array ({err})"}
