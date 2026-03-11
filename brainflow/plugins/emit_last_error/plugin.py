"""emit_last_error

Emit a self-repair diagnostic candidate into outbox if the workflow encountered an error
but continued (engine step.allow_fail=true).

This is a bridge from Planner -> Self-repair: errors become observable artifacts.

Input:
- last_error: dict like {i,name,kind,error}
- run_id/trace_path: optional metadata

Output:
- {ok:true, skipped:true} if no error
- otherwise writes a candidate kind=self_repair_report
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from plugins.candidate_write.plugin import run as cand_write


def run(last_error: Any = None, run_id: str = "", trace_path: str = "") -> Dict[str, Any]:
    # Normalize
    if not isinstance(last_error, dict):
        return {"ok": True, "skipped": True, "reason": "no_last_error"}

    err = str(last_error.get("error") or "").strip()
    if not err:
        return {"ok": True, "skipped": True, "reason": "empty_error"}

    item = {
        "kind": "self_repair_report",
        "run_id": run_id,
        "trace": trace_path,
        "where": {
            "i": last_error.get("i"),
            "name": last_error.get("name"),
            "kind": last_error.get("kind"),
        },
        "error": err,
        "suggested_next": "Inspect trace + step plugin; fix JSON extraction/command length; add deterministic fallback.",
        # Dedup by error signature (good enough for now)
        "dedup_hash": f"err:{(str(last_error.get('name') or '') + '|' + err)[:160]}",
    }

    w = cand_write(item=item)
    return {"ok": True, "written": w}
