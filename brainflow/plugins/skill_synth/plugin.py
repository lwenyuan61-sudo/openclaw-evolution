"""Skill Synthesizer (MVP): propose a new skill/plugin/workflow skeleton.

This plugin does NOT call an LLM yet; it produces a structured spec based on a gap description.
Later we can connect it to an LLM in a sandbox and require tests.
"""

from __future__ import annotations

import time
from typing import Any, Dict


def run(gap: str, kind: str = "plugin") -> Dict[str, Any]:
    ts = int(time.time())
    name = f"skill_{ts}"
    if kind == "workflow":
        return {
            "ok": True,
            "kind": "workflow_spec",
            "name": name,
            "description": f"Auto-proposed workflow to address gap: {gap}",
            "steps": [
                "forage/search",
                "extract key claims + urls",
                "evaluate evidence level",
                "write semantic card",
            ],
        }

    # plugin
    return {
        "ok": True,
        "kind": "plugin_spec",
        "name": name,
        "description": f"Auto-proposed plugin to address gap: {gap}",
        "inputs": {"text": "input text"},
        "outputs": "structured result",
        "tests": [
            {"name": "happy_path", "input": {"text": "example"}, "expect": "non-empty"},
            {"name": "edge_empty", "input": {"text": ""}, "expect": "handles empty"},
        ],
    }
