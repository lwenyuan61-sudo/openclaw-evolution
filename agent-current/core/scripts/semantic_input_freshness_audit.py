from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
AUTO = ROOT / "autonomy"
OUT = STATE / "semantic_input_freshness_audit.json"

PATHS = {
    "resource": CORE / "resource-state.json",
    "owner_chat": STATE / "owner_chat_signal_state.json",
    "conversation": STATE / "conversation_insights.json",
    "screen": STATE / "screen_semantic_summary.json",
    "screen_state": STATE / "screen_state.json",
    "semantic": STATE / "semantic_signal_layer.json",
    "opportunity": STATE / "lee_opportunity_review.json",
    "help": STATE / "lee_service_help_evidence.json",
    "working_memory": STATE / "resident_working_memory.json",
    "goal_register": AUTO / "goal-register.json",
}


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_loadError": f"{type(exc).__name__}: {exc}"}


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def age_minutes(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return round((now() - dt).total_seconds() / 60.0, 3)


def latest_owner_chat(conversation: dict) -> dict:
    bridge = conversation.get("conversationInsight", {}).get("ownerChatBridge") if isinstance(conversation.get("conversationInsight"), dict) else None
    if not isinstance(bridge, dict):
        bridge = conversation.get("ownerChatBridge", {}) if isinstance(conversation.get("ownerChatBridge"), dict) else {}
    return bridge


def main() -> None:
    data = {name: load(path) for name, path in PATHS.items()}
    resource = data["resource"].get("resourcePressure", {}) if isinstance(data["resource"].get("resourcePressure"), dict) else {}
    owner = data["owner_chat"]
    conv_bridge = latest_owner_chat(data["conversation"])
    screen = data["screen"]
    screen_state = data["screen_state"]
    semantic = data["semantic"]
    opportunity = data["opportunity"]
    help_evidence = data["help"]

    screen_hash_match = bool(screen.get("screenHash") and screen.get("screenHash") == screen_state.get("screenHash"))
    screen_age = age_minutes(screen.get("timestamp") or screen.get("capturedAt"))
    screen_state_age = age_minutes(screen_state.get("capturedAt"))

    owner_state_at = owner.get("lastOwnerChatIngestedAt") or owner.get("latestInboxOwnerSignalAt")
    conv_latest_at = conv_bridge.get("latestInboxOwnerSignalAt") or conv_bridge.get("lastOwnerChatIngestedAt")
    owner_consistent = bool(
        (not owner_state_at and not conv_latest_at)
        or (owner_state_at and conv_latest_at and owner_state_at == conv_latest_at)
        or conv_bridge.get("staleDespiteInbox") is False
    )

    reach_gate = opportunity.get("reachOutGate", {}) if isinstance(opportunity.get("reachOutGate"), dict) else {}
    missing = list(reach_gate.get("missingEvidence", []) or [])
    must = list(reach_gate.get("mustRequirements", []) or [])
    semantic_obs = list(semantic.get("observations", []) or [])
    candidate_requests = list(semantic.get("candidateRequests", []) or [])
    semantic_pressure = float(semantic.get("semanticPressure", 0.0) or 0.0)
    only_non_external_requirement = bool(must and set(str(item) for item in must).issubset({"not-an-external-signal"}))
    gate_has_actionable_missing_evidence = bool(missing or (must and not only_non_external_requirement))

    findings = []
    if resource.get("level") in {"warning", "critical"}:
        findings.append({"id": "resource-pressure", "severity": "high", "summary": "Resource pressure requires compression/offload before further evolution.", "recommendedPatch": "defer GPU/local-heavy tasks"})
    if screen_hash_match and screen.get("classification", {}).get("labels") and "need-durable-semantic-writeback" in missing:
        findings.append({"id": "screen-semantic-not-satisfying-reachout-gate", "severity": "medium", "summary": "Current screen semantic summary matches the screen hash but reachOutGate still reports missing durable semantic writeback.", "recommendedPatch": "copy current screen semantic hash/labels into perception-state lastScreenSemanticWriteback and let reachOutGate consume it when hash matches"})
    if not owner_consistent:
        findings.append({"id": "owner-chat-state-inconsistent", "severity": "medium", "summary": "Owner chat bridge state and conversation bridge state disagree.", "recommendedPatch": "refresh owner_chat_signal_state from bounded inbox bridge"})
    if any(obs.get("id") == "candidate-generation-bottleneck" for obs in semantic_obs) and not candidate_requests:
        if gate_has_actionable_missing_evidence or semantic_pressure >= 0.55:
            findings.append({"id": "candidate-bottleneck-without-request", "severity": "medium", "summary": "Semantic layer observes candidate-generation bottleneck without live candidateRequests.", "recommendedPatch": "ensure high-value semantic freshness audit request is kept until completed"})
        else:
            findings.append({"id": "candidate-bottleneck-benign-maintain", "severity": "low", "summary": "Semantic layer still observes ambient candidate-generation pressure, but reachOutGate has no actionable missing evidence and semantic pressure is below candidate threshold.", "recommendedPatch": None})

    if not findings:
        findings.append({"id": "no-missing-writeback-confirmed", "severity": "low", "summary": "Inputs appear fresh/consistent enough; wait for next non-maintenance signal before patching.", "recommendedPatch": None})

    result = {
        "timestamp": now_iso(),
        "status": "ok",
        "resourcePressure": resource,
        "inputs": {
            "ownerChat": {
                "stateAt": owner_state_at,
                "conversationLatestAt": conv_latest_at,
                "conversationStaleDespiteInbox": conv_bridge.get("staleDespiteInbox"),
                "consistent": owner_consistent,
                "ageMinutes": age_minutes(owner_state_at),
            },
            "screenSemantic": {
                "screenHash": screen.get("screenHash"),
                "screenStateHash": screen_state.get("screenHash"),
                "hashMatch": screen_hash_match,
                "labels": screen.get("classification", {}).get("labels", []),
                "semanticAgeMinutes": screen_age,
                "screenStateAgeMinutes": screen_state_age,
            },
            "reachOutGate": {
                "decision": reach_gate.get("decision"),
                "shouldSurface": reach_gate.get("shouldSurface"),
                "missingEvidence": missing,
                "mustRequirements": must,
                "helpEvidence": reach_gate.get("helpEvidence"),
            },
            "helpEvidence": {
                "status": help_evidence.get("status") or help_evidence.get("verification", {}).get("status") if isinstance(help_evidence.get("verification"), dict) else help_evidence.get("status"),
                "recommendation": help_evidence.get("recommendation", {}),
            },
            "semanticSignalLayer": {
                "recommendedAction": semantic.get("recommendedAction"),
                "semanticPressure": semantic.get("semanticPressure"),
                "candidateRequestIds": [item.get("id") for item in candidate_requests if isinstance(item, dict)],
                "observationIds": [item.get("id") for item in semantic_obs if isinstance(item, dict)],
                "gateHasActionableMissingEvidence": gate_has_actionable_missing_evidence,
                "onlyNonExternalRequirement": only_non_external_requirement,
            },
        },
        "findings": findings,
        "nextPatch": findings[0].get("recommendedPatch"),
        "policy": {"readOnly": True, "externalWrites": False, "gpuHeavyWork": False},
    }
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
