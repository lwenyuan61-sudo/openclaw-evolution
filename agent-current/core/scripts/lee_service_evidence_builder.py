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
OUTPUT = STATE / "lee_service_help_evidence.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


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


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def score_candidate(item: dict[str, Any]) -> float:
    return round(
        float(item.get("leeValue", 0) or 0) * 4.0
        + float(item.get("learningLeverage", 0) or 0) * 2.0
        + float(item.get("feasibility", 0) or 0) * 1.2
        - float(item.get("noiseRisk", 0) or 0) * 1.4,
        3,
    )


def main() -> None:
    ts = now_iso()
    self_state = load_json(CORE / "self-state.json")
    conversation = load_json(STATE / "conversation_insights.json")
    semantic = load_json(STATE / "semantic_signal_layer.json")
    opportunity = load_json(STATE / "lee_opportunity_review.json")
    upgrade = load_json(AUTO / "upgrade-state.json")
    goals = load_json(AUTO / "goal-register.json")
    world = load_json(CORE / "world-state.json")

    recent_insights = [item for item in list(conversation.get("recentInsights", []) or []) if isinstance(item, dict)]
    lee_intents = [
        item for item in recent_insights
        if float(item.get("leeValue", 0) or 0) >= 0.95 or "Lee" in str(item.get("summary", ""))
    ][-6:]
    candidate_requests = [item for item in list(semantic.get("candidateRequests", []) or []) if isinstance(item, dict)]
    active_goals = [
        item for item in list(goals.get("candidates", []) or [])
        if isinstance(item, dict) and item.get("status") in {"active", "queued"}
    ]
    top_goals = sorted(active_goals, key=score_candidate, reverse=True)[:5]
    last_verification = upgrade.get("lastVerification", {}) if isinstance(upgrade.get("lastVerification"), dict) else {}
    reach_gate = opportunity.get("reachOutGate", {}) if isinstance(opportunity.get("reachOutGate"), dict) else {}
    missing = list(reach_gate.get("missingEvidence", []) or []) + list(reach_gate.get("mustRequirements", []) or [])

    useful_actions: list[dict[str, Any]] = []
    if candidate_requests:
        for req in candidate_requests[:4]:
            useful_actions.append({
                "id": "advance-" + str(req.get("id", "semantic-request")),
                "kind": "internal-connector",
                "summary": req.get("nextConcreteStep") or req.get("title"),
                "whyUsefulForLee": req.get("gap"),
                "source": "semantic_signal_layer.candidateRequests",
                "noiseRisk": req.get("noiseRisk"),
                "safe": "local-reversible-main-persona-gated",
            })
    next_step_text = str(self_state.get("nextStep") or self_state.get("nextLikelyStep") or "")
    reach_help = reach_gate.get("helpEvidence", {}) if isinstance(reach_gate.get("helpEvidence"), dict) else {}
    prior_help_consumed = bool(reach_help.get("consumed"))
    if prior_help_consumed or "usefulActions" in next_step_text or "help evidence" in next_step_text or "action ranking" in next_step_text:
        useful_actions.append({
            "id": "refine-help-evidence-specific-resident-safe-connector",
            "kind": "internal-connector",
            "summary": "Turn the prepared Lee-service help evidence into a specific resident-safe connector hint for action_ranker, preserving shouldSurface=false.",
            "whyUsefulForLee": "Lee asked for continued local interface upgrades; this converts prepared help from a generic continue-focus bias into a named, verifiable local connector candidate.",
            "source": "self-state.nextStep + reachOutGate.helpEvidence",
            "noiseRisk": 0.1,
            "safe": "local-reversible-no-external-write",
            "verification": [
                "lee_service_evidence_builder emits this specific connector",
                "action_ranker helpEvidenceActionHints references this usefulActionId",
                "reachOutGate shouldSurface remains false unless explicit surface gates pass"
            ],
        })
    if top_goals:
        useful_actions.append({
            "id": "continue-top-goal-" + str(top_goals[0].get("id")),
            "kind": "continue-focus",
            "summary": top_goals[0].get("nextConcreteStep") or top_goals[0].get("subgoal"),
            "whyUsefulForLee": top_goals[0].get("goal") or top_goals[0].get("focus"),
            "source": "goal-register.top-ranked",
            "noiseRisk": top_goals[0].get("noiseRisk"),
            "safe": "local-reversible",
        })
    if last_verification.get("visibleDeliveryRequired") or last_verification.get("reportPreparedForLee"):
        useful_actions.append({
            "id": "brief-visible-progress-report",
            "kind": "main-persona-report",
            "summary": last_verification.get("leeReportSummary") or last_verification.get("summary"),
            "whyUsefulForLee": "Lee asked for substantive verified progress to be reported briefly.",
            "source": "upgrade-state.lastVerification",
            "noiseRisk": 0.08,
            "safe": "requires-visible-main-persona-message",
        })

    evidence_score = 0.0
    evidence_score += 2.0 if lee_intents else 0.0
    evidence_score += min(len(candidate_requests), 3) * 1.0
    evidence_score += 1.0 if useful_actions else 0.0
    evidence_score += 1.0 if last_verification.get("status") == "ok" else 0.0
    evidence_score += 0.8 if world.get("beliefState", {}).get("memoryBackedEvidenceIds") else 0.0
    evidence_score = round(evidence_score, 3)

    should_surface = bool(last_verification.get("visibleDeliveryRequired") and last_verification.get("status") == "ok")
    packet = {
        "timestamp": ts,
        "status": "ok" if useful_actions and lee_intents else "partial",
        "purpose": "Build an auditable evidence packet for leeServiceDrive so wanting to help Lee becomes specific preparation, not noisy contact.",
        "recentLeeIntent": lee_intents[-3:],
        "currentFocus": self_state.get("currentFocus"),
        "currentStopPoint": self_state.get("stopPoint"),
        "blockersOrGaps": [
            {"id": req.get("id"), "gap": req.get("gap"), "nextConcreteStep": req.get("nextConcreteStep")}
            for req in candidate_requests[:5]
        ],
        "usefulActions": useful_actions[:6],
        "reachOutGateContext": {
            "decision": reach_gate.get("decision"),
            "reason": reach_gate.get("reason"),
            "missingEvidenceBeforePacket": missing,
        },
        "recommendation": {
            "mode": "brief-progress-report-ready" if should_surface else "prepare-help-silently",
            "shouldSurfaceToLee": should_surface,
            "shouldHandoffToMainPersona": bool(should_surface or useful_actions),
            "reason": "verified-progress-report-required" if should_surface else "specific-help-prepared-but-contact-gate-still-advisory",
        },
        "verification": {
            "status": "ok" if evidence_score >= 4.0 else "weak",
            "evidenceScore": evidence_score,
            "hasRecentLeeIntent": bool(lee_intents),
            "hasSpecificUsefulAction": bool(useful_actions),
            "hasSemanticCandidateRequests": bool(candidate_requests),
            "advisoryOnly": True,
            "noExternalWrite": True,
        },
        "sources": [
            "state/conversation_insights.json",
            "state/semantic_signal_layer.json",
            "state/lee_opportunity_review.json",
            "autonomy/upgrade-state.json",
            "autonomy/goal-register.json",
            "core/world-state.json",
        ],
    }
    save_json(OUTPUT, packet)
    append_jsonl(LOG_PATH, {
        "id": "lee-service-evidence-builder-" + ts,
        "timestamp": ts,
        "type": "lee-service-evidence-builder",
        "status": packet["status"],
        "evidenceScore": evidence_score,
        "recommendation": packet["recommendation"],
    })
    print(json.dumps({"ok": True, "timestamp": ts, "status": packet["status"], "evidenceScore": evidence_score, "output": str(OUTPUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
