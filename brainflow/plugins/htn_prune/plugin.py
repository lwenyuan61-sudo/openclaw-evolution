"""htn_prune

Prune low-feasibility tasks from an HTN decomposition.

- Evaluates each child task feasibility using feasibility_judge (heuristic by default).
- If FeasibilityScore < threshold -> drop the child.
- Also remove that subtree from queue_manager (best-effort) to delete descendants.

Returns updated HTN object with children pruned.
"""

from __future__ import annotations

from typing import Any, Dict, List

from plugins.feasibility_judge.plugin import run as feas_run
from plugins.queue_manager.plugin import remove_subtree


def _get_score(feas: Any) -> float:
    try:
        if isinstance(feas, dict) and "FeasibilityScore" in feas:
            return float(feas.get("FeasibilityScore") or 0.0)
        if isinstance(feas, (int, float)):
            return float(feas)
    except Exception:
        pass
    return 0.0


def run(htn: Dict[str, Any], threshold: float = 2.0) -> Dict[str, Any]:
    """Return a pruned HTN object with the SAME top-level shape as htn_decompose output.

    Output keys: ok, parent, children, mode, pruned, kept_n, pruned_n, threshold
    """
    if not isinstance(htn, dict):
        return {"ok": True, "parent": {}, "children": [], "mode": "pruned", "pruned": [], "kept_n": 0, "pruned_n": 0, "threshold": threshold}

    parent = htn.get("parent") if isinstance(htn.get("parent"), dict) else {}
    children = htn.get("children") if isinstance(htn.get("children"), list) else []

    kept: List[Dict[str, Any]] = []
    pruned: List[Dict[str, Any]] = []

    for ch in children:
        if not isinstance(ch, dict):
            continue
        # Ensure feasibility exists (compute if absent)
        feas = ch.get("feasibility")
        if not isinstance(feas, dict) or "FeasibilityScore" not in feas:
            try:
                feas = feas_run(task=ch)
                ch = {**ch, "feasibility": feas}
            except Exception:
                feas = ch.get("feasibility")

        score = _get_score(feas)
        if score < float(threshold):
            pruned.append({**ch, "_feas_score": score})
            # Best-effort: remove already-queued subtree across runs
            try:
                tid = str(ch.get("id") or "")
                if tid:
                    remove_subtree(tid)
            except Exception:
                pass
        else:
            kept.append(ch)

    mode = str(htn.get("mode") or "")
    mode = (mode + "+pruned").strip("+")

    return {
        "ok": True,
        "parent": parent,
        "children": kept,
        "mode": mode,
        "pruned": pruned,
        "kept_n": len(kept),
        "pruned_n": len(pruned),
        "threshold": float(threshold),
    }
