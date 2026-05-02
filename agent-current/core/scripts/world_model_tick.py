from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
WORLD_STATE = CORE / "world-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tail_jsonl(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"unparsed": line[:240]})
    return rows


def score_candidate(item: dict[str, Any]) -> float:
    return round(
        float(item.get("leeValue", 0) or 0) * 4.0
        + float(item.get("learningLeverage", 0) or 0) * 2.0
        + float(item.get("continuityWeight", 0) or 0) * 1.5
        + float(item.get("feasibility", 0) or 0) * 1.0
        - float(item.get("noiseRisk", 0) or 0) * 1.2,
        3,
    )


def main() -> None:
    timestamp = now_iso()
    self_state = load_json(CORE / "self-state.json")
    perception = load_json(CORE / "perception-state.json")
    action_state = load_json(CORE / "action-state.json")
    learning = load_json(CORE / "learning-state.json")
    procedural = load_json(CORE / "procedural-memory.json")
    continuity = load_json(AUTO / "continuity-state.json")
    goals = load_json(AUTO / "goal-register.json")
    upgrade = load_json(AUTO / "upgrade-state.json")
    reflection = load_json(STATE / "resident_reflection.json")
    opportunity = load_json(STATE / "lee_opportunity_review.json")
    conversation = load_json(STATE / "conversation_insights.json")
    semantic_layer = load_json(STATE / "semantic_signal_layer.json")
    experiments = tail_jsonl(AUTO / "experiment-log.jsonl", 30)

    recent_signals = perception.get("lastProbeSignals") or []
    current_focus = self_state.get("currentFocus")
    mode = self_state.get("currentMode") or load_json(CORE / "session-mode.json").get("mode")
    counters = learning.get("counters", {}) if isinstance(learning.get("counters"), dict) else {}
    s2_debt = int(counters.get("s2CompileDebt", 0) or 0)
    recent_low_value_ticks = 0
    for item in reversed(experiments):
        if not isinstance(item, dict):
            continue
        chosen = item.get("chosenCandidate") if isinstance(item.get("chosenCandidate"), dict) else None
        selected = item.get("selected") or (chosen.get("id") if isinstance(chosen, dict) else None)
        if item.get("status") == "maintained-no-handoff" or selected == "maintain-current-upgrade-loop":
            recent_low_value_ticks += 1
            continue
        if selected:
            break

    active_goals = [
        g for g in goals.get("candidates", []) or []
        if isinstance(g, dict) and g.get("status") in {"active", "queued"}
    ]
    ranked_goals = sorted(active_goals, key=score_candidate, reverse=True)[:5]

    predictions: list[dict[str, Any]] = []
    if recent_low_value_ticks >= 3:
        predictions.append({
            "id": "low-value-maintenance-loop",
            "confidence": 0.78,
            "prediction": "If no new evidence source is used, the resident loop will keep selecting maintenance ticks with limited Lee-facing value.",
            "expectedNext": "autonomy_info_scout should trigger web scout or route a queued goal instead of pure maintain.",
            "falsifyBy": "next autonomy_upgrade_tick selects a non-maintenance connector or a real blocker appears",
        })
    if recent_signals:
        predictions.append({
            "id": "fresh-signal-needs-semantic-gate",
            "confidence": 0.64,
            "prediction": "Fresh perception/workspace signals may be noise unless semantic writeback or verification raises value.",
            "expectedNext": "stay S1 unless opportunity evidence crosses surface/handoff thresholds",
            "falsifyBy": "opportunity_review shouldSurface/shouldHandoff becomes true",
        })
    if s2_debt >= 3:
        predictions.append({
            "id": "s2-compile-pressure",
            "confidence": 0.82,
            "prediction": "Verified S2 outcomes are accumulating faster than S1 compression.",
            "expectedNext": "select compile-more-s2-into-s1 or fold episodes into an existing S1 family",
            "falsifyBy": "s2CompileDebt falls below 3 after coverage update",
        })
    if ranked_goals:
        top = ranked_goals[0]
        predictions.append({
            "id": "highest-ranked-goal-pressure",
            "confidence": 0.7,
            "prediction": f"The most promising queued/active goal is {top.get('id')}.",
            "expectedNext": str(top.get("nextConcreteStep") or top.get("subgoal") or "route through upgrade tick"),
            "falsifyBy": "initiative_review or autonomy_upgrade_tick ranks another connector higher with stronger evidence",
        })

    memory_loop = conversation.get("memoryControlLoop", {}) if isinstance(conversation.get("memoryControlLoop"), dict) else {}
    recent_insights = [
        item for item in list(conversation.get("recentInsights", []) or [])
        if isinstance(item, dict)
    ]
    high_value_memory = [
        item for item in recent_insights
        if float(item.get("leeValue", 0) or 0) >= 0.95 or float(item.get("upgradeRelevance", 0) or 0) >= 0.9
    ][:5]
    semantic_requests = [
        item for item in list(semantic_layer.get("candidateRequests", []) or [])
        if isinstance(item, dict)
    ][:5]
    if memory_loop.get("enabled") and high_value_memory:
        predictions.append({
            "id": "memory-backed-action-pressure",
            "confidence": 0.76,
            "prediction": "Recent conversation memory contains high-value Lee/autonomy signals that should influence the next resident action candidate instead of remaining passive notes.",
            "expectedNext": "world-model/action candidates should include a memoryControlLoop-backed internal action and upgrade tick should prefer matching connector work.",
            "falsifyBy": "action_ranker/world_state ignore memory-backed candidates for multiple pulses or semantic requests disappear without completion",
            "memoryEvidenceIds": [item.get("id") for item in high_value_memory],
            "semanticRequestIds": [item.get("id") for item in semantic_requests],
        })

    action_candidates = [
        *([
            {
                "action": "continue-focus",
                "expectedOutcome": "keep the current autonomy-upgrade track active because high-value Lee conversation memory is relevant to current work",
                "cost": "low",
                "risk": "low-internal",
                "when": "memoryControlLoop has recent high-value Lee/autonomy evidence",
                "source": "memoryControlLoop.read",
                "memoryBacked": True,
                "evidenceIds": [item.get("id") for item in high_value_memory],
                "semanticRequestIds": [item.get("id") for item in semantic_requests],
            },
            {
                "action": "run-autonomy-upgrade-tick",
                "expectedOutcome": "turn memory-backed semantic requests into the next verified connector candidate",
                "cost": "medium",
                "risk": "low-internal-main-persona-gated",
                "when": "semantic_signal_layer has candidateRequests derived from conversation memory or Lee-service pressure",
                "source": "memoryControlLoop.read -> semanticSignalLayer",
                "memoryBacked": True,
                "evidenceIds": [item.get("id") for item in high_value_memory],
                "semanticRequestIds": [item.get("id") for item in semantic_requests],
            },
        ] if memory_loop.get("enabled") and high_value_memory else []),
        {
            "action": "continue-focus",
            "expectedOutcome": "preserve continuity and avoid unnecessary churn",
            "cost": "low",
            "risk": "low",
            "when": "no prediction has high urgency",
        },
        {
            "action": "run-autonomy-upgrade-tick",
            "expectedOutcome": "convert the highest pressure connector into a verified state/log update",
            "cost": "medium",
            "risk": "low-internal",
            "when": "a prediction indicates real connector pressure",
        },
        {
            "action": "run-autonomy-web-scout",
            "expectedOutcome": "bring in new external ideas when internal loop is stale",
            "cost": "medium",
            "risk": "external-read-only",
            "when": "low-value-maintenance-loop remains active and cooldown allows",
        },
    ]

    world_state = {
        "timestamp": timestamp,
        "purpose": "compact predictive belief layer for the resident control plane",
        "beliefState": {
            "currentFocus": current_focus,
            "mode": mode,
            "currentTrackId": self_state.get("currentTrackId") or continuity.get("currentTrackId"),
            "recentSignalCount": len(recent_signals),
            "recentLowValueMaintenanceTicks": recent_low_value_ticks,
            "s2CompileDebt": s2_debt,
            "topGoalIds": [g.get("id") for g in ranked_goals],
            "memoryControlLoopEnabled": bool(memory_loop.get("enabled")),
            "memoryBackedEvidenceIds": [item.get("id") for item in high_value_memory],
            "semanticCandidateRequestIds": [item.get("id") for item in semantic_requests],
            "lastOpportunityDecision": opportunity.get("decision") or opportunity.get("lastOpportunityDecision"),
            "lastReflectionScore": reflection.get("totalScore"),
        },
        "predictions": predictions,
        "actionCandidates": action_candidates,
        "verificationPlan": [
            "Compare next autonomy_upgrade_tick selection against predictions.",
            "Check whether low-value maintenance streak falls after web scout / goal routing.",
            "Use consistency_check.py and module_linkage_audit.py after adding new connectors.",
        ],
        "sources": [
            "core/self-state.json",
            "core/perception-state.json",
            "core/action-state.json",
            "core/learning-state.json",
            "core/procedural-memory.json",
            "autonomy/continuity-state.json",
            "autonomy/goal-register.json",
            "autonomy/upgrade-state.json",
            "state/resident_reflection.json",
            "state/lee_opportunity_review.json",
            "state/conversation_insights.json",
            "state/semantic_signal_layer.json",
        ],
    }
    save_json(WORLD_STATE, world_state)
    print(json.dumps({
        "ok": True,
        "timestamp": timestamp,
        "predictionCount": len(predictions),
        "topPredictions": [p.get("id") for p in predictions[:3]],
        "worldStatePath": str(WORLD_STATE),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
