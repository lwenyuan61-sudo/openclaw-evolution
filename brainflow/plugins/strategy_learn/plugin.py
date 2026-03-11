"""Strategy learning (now deterministic).

Originally LLM-led, but OpenClaw agent cannot read local files by path and Windows CLI
argument length limits make large prompts brittle.

This module now produces a small, explicit strategy pack deterministically.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional


DEFAULT_STRATEGIES: Dict[str, Any] = {
    "schema": "brainflow.strategies.v1",
    "t": 0,
    "principles": [
        "Prefer reversible changes.",
        "Prefer actions that increase execution reliability.",
        "When uncertain, produce a small, testable deliverable.",
    ],
    "policies": {
        "self_modify": {
            "enabled": True,
            "allowlist": ["workflows/*.yaml", "plugins/**/*.py", "core/**/*.py", "memory/procedural/*.json"],
        },
        "external_actions": {"enabled": False, "allowlist": []},
    },
    "playbooks": {
        "json_parse_fail": ["extract first {...} block", "repair with JSON-only prompt", "fallback to safe subgoal"],
        "loop_detected": ["increase interval", "introduce novelty constraint", "pause and summarize"],
        "cli_arg_too_long": [
            "omit large fields from prompts (trace_tail, semantic_text)",
            "cap prompt length aggressively",
            "prefer deterministic fallback over LLM for bookkeeping modules",
        ],
    },
    "next_cycle_adjustments": [],
    "sources": ["deterministic"],
}


def _load_json(path: str) -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, dict):
                return obj
    except Exception:
        pass
    return None


def run(thinking: str = "minimal") -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(proc_dir, exist_ok=True)

    out_path = os.path.join(proc_dir, "strategies.json")
    now = int(time.time())

    strategies: Dict[str, Any] = json.loads(json.dumps(DEFAULT_STRATEGIES))
    strategies["t"] = now

    # Preserve any owner-edited strategies fields if present.
    prev = _load_json(out_path) or {}
    if isinstance(prev, dict) and prev.get("schema") == "brainflow.strategies.v1":
        for k in ["principles", "playbooks", "next_cycle_adjustments"]:
            if k in prev:
                strategies[k] = prev[k]
        if isinstance(prev.get("policies"), dict):
            strategies["policies"] = prev["policies"]

    # Enforce the owner-approved self_modify policy: enabled + allowlist.
    strategies.setdefault("policies", {})
    strategies["policies"].setdefault("self_modify", {})
    strategies["policies"]["self_modify"]["enabled"] = True
    strategies["policies"]["self_modify"].setdefault(
        "allowlist",
        ["workflows/*.yaml", "plugins/**/*.py", "core/**/*.py", "memory/procedural/*.json"],
    )

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(strategies, f, ensure_ascii=False, indent=2)

    return {"ok": True, "path": out_path, "strategies": strategies, "llm": {"ok": False, "error": "deterministic"}}
