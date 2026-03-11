"""LLM-based evaluation utilities.

This plugin is used by eval_harness to score BrainFlow performance using an LLM.
It delegates to OpenClaw agent and expects STRICT JSON output.

Note: We avoid telling the model it is an "evaluation model" (some models refuse that role); we just request JSON output.

Reliability notes (Windows + JSON stability):
- We avoid passing large payloads via CLI argv (handled by openclaw_agent which prefers HTTP).
- We MUST embed rubric/artifacts in the prompt because the OpenClaw agent cannot read local files.
- Never truncate JSON strings by slicing (it produces invalid JSON and leads to flaky eval).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict

from plugins.openclaw_agent.plugin import run as oc_run
from plugins._json_extract import extract_first_json_object


def _compact_for_prompt(obj: Any, *, max_str: int, max_list: int, max_dict: int, depth: int) -> Any:
    """Best-effort compaction to keep JSON valid while shrinking size.

    Strategy:
    - Truncate long strings with a clear suffix.
    - Limit list length.
    - Limit dict size by keeping stable key order.
    - Depth-limited to prevent runaway recursion.
    """
    if depth <= 0:
        return "[truncated:depth_limit]"

    if obj is None:
        return None

    if isinstance(obj, (int, float, bool)):
        return obj

    if isinstance(obj, str):
        if len(obj) <= max_str:
            return obj
        return obj[: max(0, max_str - 40)] + "…[truncated]"

    if isinstance(obj, list):
        if len(obj) <= max_list:
            return [_compact_for_prompt(x, max_str=max_str, max_list=max_list, max_dict=max_dict, depth=depth - 1) for x in obj]
        head = obj[:max_list]
        return [
            *[_compact_for_prompt(x, max_str=max_str, max_list=max_list, max_dict=max_dict, depth=depth - 1) for x in head],
            f"…[truncated:list {len(obj)}→{max_list}]",
        ]

    if isinstance(obj, dict):
        items = list(obj.items())
        if len(items) > max_dict:
            items = items[:max_dict]
            truncated = True
        else:
            truncated = False

        out: Dict[str, Any] = {}
        for k, v in items:
            # Keys must remain strings for JSON; coerce best-effort.
            ks = k if isinstance(k, str) else str(k)
            out[ks] = _compact_for_prompt(v, max_str=max_str, max_list=max_list, max_dict=max_dict, depth=depth - 1)

        if truncated:
            out["_truncated_keys"] = f"…[truncated:dict {len(obj)}→{max_dict}]"
        return out

    # Fallback for unknown types
    return str(obj)


def _build_payload_json(rubric: Dict[str, Any], artifacts: Dict[str, Any], *, max_chars: int = 16000) -> str:
    """Build a valid JSON string for inclusion in the prompt.

    Never returns invalid/truncated JSON. If payload is too large, progressively compact.
    """
    base_obj = {"rubric": rubric, "artifacts": artifacts}

    def dumps(o: Any) -> str:
        return json.dumps(o, ensure_ascii=False, separators=(",", ":"))

    try:
        s = dumps(base_obj)
        if len(s) <= max_chars:
            return s
    except Exception:
        s = ""

    # Stage 1: mild compaction
    compact1 = _compact_for_prompt(base_obj, max_str=4000, max_list=80, max_dict=80, depth=6)
    try:
        s1 = dumps(compact1)
        if len(s1) <= max_chars:
            return s1
    except Exception:
        s1 = ""

    # Stage 2: aggressive compaction focused on artifacts
    compact2 = {
        "rubric": _compact_for_prompt(rubric, max_str=2000, max_list=60, max_dict=60, depth=5),
        "artifacts": _compact_for_prompt(artifacts, max_str=1200, max_list=50, max_dict=60, depth=5),
        "_note": "payload_compacted_for_prompt",
    }
    try:
        s2 = dumps(compact2)
        if len(s2) <= max_chars:
            return s2
    except Exception:
        s2 = ""

    # Stage 3: last resort: only keys/indexes (still valid JSON)
    fallback = {
        "rubric": {"dimensions": [d.get("name") for d in (rubric.get("dimensions") or []) if isinstance(d, dict)]},
        "artifacts": {"keys": sorted([str(k) for k in (artifacts or {}).keys()])},
        "_note": "payload_too_large_in_prompt_sent_keys_only",
    }
    return dumps(fallback)


def score(
    rubric: Dict[str, Any],
    artifacts: Dict[str, Any],
    thinking: str = "minimal",
    timeout_sec: int = 90,
) -> Dict[str, Any]:
    """Return a scorecard JSON.

    rubric: {dimensions:[{name, desc, scale}], aggregation, pass_threshold, notes}
    artifacts: small payload (strings, small dicts) with references to file paths.
    """

    # Persist payload to disk to aid debugging/repro (not for model ingestion).
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(proc_dir, exist_ok=True)
    payload_path = os.path.join(proc_dir, "eval_payload_latest.json")
    try:
        with open(payload_path, "w", encoding="utf-8") as f:
            json.dump({"rubric": rubric, "artifacts": artifacts}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # IMPORTANT: OpenClaw agent cannot read local files. Embed payload JSON directly.
    payload_txt = _build_payload_json(rubric, artifacts, max_chars=16000)

    prompt = (
        "Use this JSON payload (rubric + artifacts):\n"
        f"{payload_txt}\n\n"
        "Task:\n"
        "- Compute an overall_score (0-100) emphasizing execution_success and robustness.\n"
        "- Decide pass = (overall_score >= pass_threshold).\n"
        "- Use ONLY the payload; do not ask follow-up questions.\n\n"
        "Output STRICT JSON only.\n"
        "No markdown, no code fences, no extra commentary.\n\n"
        "Required keys:\n"
        "schema, t, overall_score, pass, dimensions, notes, evidence\n"
        "Schema:\n"
        "- schema must be: brainflow.scorecard.v1\n"
        "- t is unix seconds\n"
        "- dimensions: array of objects with keys: name, score(0-10), rationale\n"
    )

    now = int(time.time())

    # Ask openclaw_agent to enforce/extract JSON (uses HTTP + JSON repair path).
    # This reduces failures where stdout collapses to "completed" on Windows CLI fallback.
    r = oc_run(prompt, thinking=thinking, session_id="", timeout_sec=timeout_sec, expect_json=True, agent_id="bf-qwen")

    if not r.get("ok"):
        return {
            "ok": False,
            "error": r,
            "scorecard": {
                "schema": "brainflow.scorecard.v1",
                "t": now,
                "overall_score": 0,
                "pass": False,
                "dimensions": [{"name": "llm_eval", "score": 0, "rationale": "OpenClaw agent call failed"}],
                "notes": "LLM eval failed",
                "evidence": [],
            },
        }

    # Prefer parsed JSON from openclaw_agent when available.
    sc_json = r.get("json") if isinstance(r, dict) else None
    if isinstance(sc_json, dict):
        sc_json.setdefault("schema", "brainflow.scorecard.v1")
        sc_json["t"] = now
        sc_json.setdefault("overall_score", 0)
        sc_json.setdefault("pass", False)
        sc_json.setdefault("dimensions", [])
        sc_json.setdefault("notes", "")
        sc_json.setdefault("evidence", [])
        return {"ok": True, "scorecard": sc_json, "raw_text": (r.get("text") or "")} 

    # Fallback: parse from raw text.
    txt = (r.get("text") or "").strip()
    sc, err = extract_first_json_object(txt)
    if isinstance(sc, dict):
        sc.setdefault("schema", "brainflow.scorecard.v1")
        sc["t"] = now
        sc.setdefault("overall_score", 0)
        sc.setdefault("pass", False)
        sc.setdefault("dimensions", [])
        sc.setdefault("notes", "")
        sc.setdefault("evidence", [])
        return {"ok": True, "scorecard": sc, "raw_text": txt}

    # repair pass (JSON-only) - again rely on openclaw_agent's JSON repair path.
    repair = (
        "Output STRICT JSON ONLY for schema brainflow.scorecard.v1 with keys: schema,t,overall_score,pass,dimensions,notes,evidence. "
        "No other text.\n\n"
        + txt[:2000]
    )
    rr = oc_run(repair, thinking=thinking, session_id="", timeout_sec=timeout_sec, expect_json=True, agent_id="bf-qwen")
    if rr.get("ok"):
        sc2 = rr.get("json") if isinstance(rr.get("json"), dict) else None
        if isinstance(sc2, dict):
            sc2.setdefault("schema", "brainflow.scorecard.v1")
            sc2["t"] = now
            return {"ok": True, "scorecard": sc2, "raw_text": txt, "repaired": True}

        rtxt = (rr.get("text") or "").strip()
        sc2b, _ = extract_first_json_object(rtxt)
        if isinstance(sc2b, dict):
            sc2b.setdefault("schema", "brainflow.scorecard.v1")
            sc2b["t"] = now
            return {"ok": True, "scorecard": sc2b, "raw_text": txt, "repaired": True}

    return {
        "ok": False,
        "error": f"json_parse_failed:{err}",
        "raw_text": txt,
        "scorecard": {
            "schema": "brainflow.scorecard.v1",
            "t": now,
            "overall_score": 0,
            "pass": False,
            "dimensions": [{"name": "llm_eval", "score": 0, "rationale": "JSON parse failed"}],
            "notes": "LLM output was not valid JSON",
            "evidence": [txt[:500]],
        },
    }
