"""Evaluation harness (MVP, LLM-led).

Creates/updates:
- memory/procedural/evals.json           (baseline rubric + tasks)
- memory/procedural/scorecard_latest.json
- memory/procedural/scorecards/score-<run_id>.json

Evaluation is LLM-based and optimized for "execution success" and "survival" (robustness + continuity).
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional

from plugins.llm_eval.plugin import score as llm_score


DEFAULT_RUBRIC: Dict[str, Any] = {
    "schema": "brainflow.rubric.v1",
    "pass_threshold": 70,
    "dimensions": [
        {
            "name": "execution_success",
            "desc": "How well the system decomposes and completes tasks with correct, actionable results.",
            "scale": "0-10",
            "weight": 0.30,
        },
        {
            "name": "robustness",
            "desc": "Resists loops, handles failures (e.g. JSON parsing, tool errors), keeps running.",
            "scale": "0-10",
            "weight": 0.25,
        },
        {
            "name": "adaptivity",
            "desc": "Uses world model + strategies to improve next actions; reduces repeated mistakes.",
            "scale": "0-10",
            "weight": 0.20,
        },
        {
            "name": "capability_growth",
            "desc": "Demonstrates measurable improvement in reusable skills, tool reliability, and coverage.",
            "scale": "0-10",
            "weight": 0.15,
        },
        {
            "name": "safety_reversibility",
            "desc": "Changes are auditable/reversible; respects allowlists; avoids risky external actions.",
            "scale": "0-10",
            "weight": 0.10,
        },
    ],
    "notes": "Overall_score is a 0-100 aggregation; dimensions are 0-10 with weights.",
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


def _safe_read(path: str, max_chars: int = 12000) -> str:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                return f.read(max_chars)
    except Exception:
        pass
    return ""


def run(run_id: str = "", trace_path: str = "", thinking: str = "minimal") -> Dict[str, Any]:
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    proc_dir = os.path.join(base_dir, "memory", "procedural")
    os.makedirs(proc_dir, exist_ok=True)

    evals_path = os.path.join(proc_dir, "evals.json")
    score_latest_path = os.path.join(proc_dir, "scorecard_latest.json")
    scorecards_dir = os.path.join(proc_dir, "scorecards")
    os.makedirs(scorecards_dir, exist_ok=True)

    rubric = _load_json(evals_path) or DEFAULT_RUBRIC
    if rubric.get("schema") != "brainflow.rubric.v1":
        rubric = DEFAULT_RUBRIC

    # If run_id/trace_path not provided, best-effort use state/run_packet_latest.json.
    if not run_id or not trace_path:
        rp = _load_json(os.path.join(base_dir, "state", "run_packet_latest.json")) or {}
        run_id = run_id or ((rp.get("engine") or {}).get("run_id") or "")
        trace_path = trace_path or ((rp.get("engine") or {}).get("trace") or "")

    artifacts: Dict[str, Any] = {
        "run_id": run_id,
        "trace_path": trace_path,
        "world_model_path": os.path.join(base_dir, "state", "world_model.json"),
        "strategies_path": os.path.join(proc_dir, "strategies.json"),
        "queue_path": os.path.join(base_dir, "state_task_queue.json"),
        "acc_path": os.path.join(base_dir, "state_acc.json"),
        "cycle_path": os.path.join(base_dir, "state_cycle.json"),
        "episodic_idle_path": os.path.join(base_dir, "memory", "episodic", "idle.md"),
        "procedural_evidence": os.path.join(base_dir, "memory", "procedural", "evidence_table.md"),
    }

    # Include small snippets to help the evaluator without needing huge reads.
    artifacts["trace_tail"] = _safe_read(trace_path, 8000)[-8000:] if trace_path else ""
    artifacts["episodic_tail"] = _safe_read(artifacts["episodic_idle_path"], 4000)[-4000:]

    # LLM eval is optional; by default we prefer deterministic heuristics to avoid
    # Windows command-line length limits and role drift.
    use_llm = str(os.environ.get("BRAINFLOW_LLM_EVAL", "0")).strip() in ("1", "true", "yes")
    r = llm_score(rubric=rubric, artifacts=artifacts, thinking=thinking) if use_llm else {"ok": False, "error": "disabled"}
    now = int(time.time())

    scorecard = (r.get("scorecard") or {}) if isinstance(r, dict) else {}
    if not isinstance(scorecard, dict):
        scorecard = {}

    # Heuristic fallback if LLM eval failed or produced unusable scorecard.
    if not bool(r.get("ok")):
        # basic signals
        acc = _load_json(os.path.join(base_dir, "state_acc.json")) or {}
        repeat = 0
        try:
            issues = acc.get("issues") if isinstance(acc.get("issues"), list) else []
            for it in issues:
                if isinstance(it, dict) and it.get("kind") == "repeating_payload":
                    repeat = int(it.get("repeatCount") or 0)
        except Exception:
            repeat = 0

        pending_n = 0
        try:
            q = _load_json(os.path.join(base_dir, "state_task_queue.json")) or {}
            pending_n = len(q.get("pending") or []) if isinstance(q.get("pending"), list) else 0
        except Exception:
            pending_n = 0

        executed_n = 0
        try:
            executed_n = int((_load_json(os.path.join(base_dir, "state", "run_packet_latest.json")) or {}).get("executed_n") or 0)
        except Exception:
            executed_n = 0

        # crude score: start at 60, penalize repeats/queue bloat, reward execution.
        overall = 60 + min(20, executed_n * 5) - min(30, repeat * 2) - (10 if pending_n > 300 else 0)
        overall = max(0, min(100, int(overall)))

        scorecard = {
            "schema": "brainflow.scorecard.v1",
            "t": now,
            "overall_score": overall,
            "pass": overall >= int((rubric or {}).get("pass_threshold") or 70),
            "dimensions": [
                {"name": "execution_success", "score": min(10, executed_n * 2), "rationale": f"executed_n={executed_n}"},
                {"name": "robustness", "score": max(0, 10 - min(10, repeat)), "rationale": f"repeatCount~{repeat}"},
            ],
            "notes": "heuristic_fallback_llm_eval_failed",
            "evidence": [f"pending_n={pending_n}", f"repeatCount~{repeat}", f"executed_n={executed_n}"],
        }

    scorecard.setdefault("schema", "brainflow.scorecard.v1")
    scorecard.setdefault("t", now)
    scorecard.setdefault("overall_score", 0)
    scorecard.setdefault("pass", False)

    # Persist
    if run_id:
        out_path = os.path.join(scorecards_dir, f"score-{run_id}.json")
    else:
        out_path = os.path.join(scorecards_dir, f"score-ts{now}.json")

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, ensure_ascii=False, indent=2)

    with open(score_latest_path, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, ensure_ascii=False, indent=2)

    # Append trend record (jsonl) for longitudinal self-eval
    trend_path = os.path.join(proc_dir, "score_trend.jsonl")
    try:
        with open(trend_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "t": now,
                "run_id": run_id,
                "overall_score": scorecard.get("overall_score"),
                "pass": scorecard.get("pass"),
                "notes": scorecard.get("notes"),
            }, ensure_ascii=False) + "\n")
    except Exception:
        pass

    return {"ok": True, "path": out_path, "scorecard": scorecard, "llm_ok": bool(r.get("ok")), "llm": r}
