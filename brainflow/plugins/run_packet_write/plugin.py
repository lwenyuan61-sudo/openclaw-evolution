"""run_packet_write

Persist a compact run packet to state/run_packet_latest.json so evaluators and notifiers
can reason about what actually happened without parsing full traces.

This is part of the self-repair infrastructure: failures become structured state.
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict


def run(
    run_id: str = "",
    trace_path: str = "",
    batch: Dict[str, Any] | None = None,
    acc: Dict[str, Any] | None = None,
    health: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    out_path = os.path.join(base_dir, "state", "run_packet_latest.json")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    pkt: Dict[str, Any] = {
        "schema": "brainflow.run_packet.v1",
        "t": int(time.time()),
        "engine": {"run_id": run_id, "trace": trace_path},
        "executed_n": int((batch or {}).get("executed_n") or 0) if isinstance(batch, dict) else 0,
        "acc": acc or {},
        "health": health or {},
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(pkt, f, ensure_ascii=False, indent=2)

    return {"ok": True, "path": out_path, "packet": pkt}
