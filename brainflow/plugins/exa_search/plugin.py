"""Exa web search via mcporter (MCP).

This plugin shells out to:
  mcporter call exa.web_search_exa query=... numResults=... type=fast

Notes:
- Requires mcporter config to include `exa` server (already configured on this host).
- Returns the raw text payload from Exa (trimmed).
"""

from __future__ import annotations

import os
import subprocess
from typing import Any


def run(query: str, num_results: int = 5, search_type: str = "fast") -> Any:
    # Allow QinWan to disable network search dynamically
    if os.environ.get("BRAINFLOW_DISABLE_SEARCH", "").strip() in ("1", "true", "yes"):
        return {"ok": False, "returncode": 0, "text": "SEARCH_DISABLED_BY_QINWAN", "cmd": []}
    # On Windows, npm bins often surface as .cmd
    exe = "mcporter.cmd"
    cfg = os.path.expandvars(r"C:\Users\15305\.openclaw\workspace\config\mcporter.json")
    cmd = [
        exe,
        "--config",
        cfg,
        "call",
        "exa.web_search_exa",
        f"query={query}",
        f"numResults={int(num_results)}",
        f"type={search_type}",
    ]
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", shell=False)
    text = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    # keep response bounded
    text = text.strip()
    if len(text) > 12000:
        text = text[:12000] + "\n...[truncated]"
    return {"ok": p.returncode == 0, "returncode": p.returncode, "text": text, "cmd": cmd}
