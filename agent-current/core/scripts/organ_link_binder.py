from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
AUTO = ROOT / "autonomy"
OUTPUT = STATE / "organ_link_graph.json"

REGISTRY_PATH = CORE / "capability-registry.json"
ORGAN_REGISTRY_PATH = CORE / "organ-registry.json"
BODY_PATH = CORE / "body-state.json"
PERCEPTION_PATH = CORE / "perception-state.json"
ACTION_PATH = CORE / "action-state.json"
SELF_PATH = CORE / "self-state.json"
ATTENTION_PATH = CORE / "attention-state.json"
HOMEOSTASIS_PATH = CORE / "homeostasis.json"
CONTINUITY_PATH = AUTO / "continuity-state.json"
SCREEN_SEMANTIC_PATH = STATE / "screen_semantic_summary.json"
DEVICE_SNAPSHOT_PATH = STATE / "device_state_snapshot.json"
SEMANTIC_SIGNAL_PATH = STATE / "semantic_signal_layer.json"
HELP_EVIDENCE_PATH = STATE / "lee_service_help_evidence.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def state_exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def ability_map(registry: dict) -> dict[str, dict]:
    return {item.get("id"): item for item in as_list(registry.get("abilities")) if isinstance(item, dict) and item.get("id")}


def source_status(sources: list[str]) -> list[dict]:
    out = []
    for src in sources:
        p = ROOT / src
        out.append({
            "path": src,
            "exists": p.exists(),
            "kind": "script" if src.endswith((".py", ".js")) else "state-or-doc",
        })
    return out


def bind(name: str, *, ability: str, organ: str, sensory: list[str], semantic: list[str], decision: list[str], action: list[str], learning: list[str], safety: list[str], runtime: dict) -> dict:
    all_paths = sensory + semantic + decision + action + learning + safety
    return {
        "id": name,
        "abilityId": ability,
        "organ": organ,
        "links": {
            "sensory": sensory,
            "semantic": semantic,
            "decision": decision,
            "action": action,
            "learning": learning,
            "safety": safety,
        },
        "linkCount": sum(1 for p in all_paths if state_exists(p)),
        "sourceStatus": source_status(all_paths),
        "runtimeEvidence": runtime,
    }


def main() -> None:
    registry = load_json(REGISTRY_PATH, {})
    body = load_json(BODY_PATH, {})
    perception = load_json(PERCEPTION_PATH, {})
    action = load_json(ACTION_PATH, {})
    self_state = load_json(SELF_PATH, {})
    attention = load_json(ATTENTION_PATH, {})
    homeostasis = load_json(HOMEOSTASIS_PATH, {})
    continuity = load_json(CONTINUITY_PATH, {})
    screen_semantic = load_json(SCREEN_SEMANTIC_PATH, {})
    device_snapshot = load_json(DEVICE_SNAPSHOT_PATH, {})
    semantic_signal = load_json(SEMANTIC_SIGNAL_PATH, {})
    help_evidence = load_json(HELP_EVIDENCE_PATH, {})

    abilities = ability_map(registry)
    recent_intents = as_list(action.get("recentIntents"))[-5:]
    recent_signals = as_list(perception.get("recentSignals"))[-5:]
    screen_labels = screen_semantic.get("classification", {}).get("labels", []) if isinstance(screen_semantic.get("classification"), dict) else []

    common_safety = [
        "core/action-state.json",
        "core/homeostasis.json",
        "core/attention-state.json",
        "core/event-routing.md",
    ]

    bindings = [
        bind(
            "screen-eye-to-cognition-to-action",
            ability="screen-observation",
            organ="screen",
            sensory=["state/screen_state.json", "state/screen_state.png", "core/perception-state.json"],
            semantic=["core/scripts/screen_semantic_summarizer.py", "state/screen_semantic_summary.json", "core/scripts/semantic_signal_layer.py", "state/semantic_signal_layer.json"],
            decision=["core/scripts/opportunity_semantic_assessor.py", "core/scripts/resident_reflection.py", "autonomy/upgrade-state.json"],
            action=["core/action-state.json", "core/scripts/resident_action.py", "core/scripts/reality_action.py"],
            learning=["core/procedural-memory.json", "core/learning-state.json", "autonomy/experiment-log.jsonl"],
            safety=common_safety,
            runtime={
                "lastScreenHash": perception.get("lastScreenHash"),
                "lastScreenCapturedAt": perception.get("lastScreenCapturedAt"),
                "semanticLabels": screen_labels,
                "activeWindow": screen_semantic.get("activeWindow", {}),
            },
        ),
        bind(
            "body-devices-to-capability-awareness",
            ability="device-sensing",
            organ="camera/microphone/speaker",
            sensory=["core/body-state.json", "state/device_state_snapshot.json", "skills/device-state/scripts/device_state.py"],
            semantic=["core/organ-registry.json", "core/capability-registry.json", "state/tool_capability_profiles.json"],
            decision=["core/scripts/task_tool_matcher.py", "core/scripts/resident_reflection.py", "autonomy/upgrade-state.json"],
            action=["skills/camera-io/scripts/camera_io.py", "skills/audio-io/scripts/audio_io.py", "skills/voice-loop/scripts/voice_loop.py"],
            learning=["core/learning-state.json", "core/procedural-memory.json", "state/tool_use_outcome_log.jsonl"],
            safety=common_safety,
            runtime={
                "bodyOrgans": sorted((body.get("organs") or {}).keys()) if isinstance(body.get("organs"), dict) else [],
                "deviceSummary": device_snapshot.get("summary", {}),
            },
        ),
        bind(
            "lee-intent-to-service-drive-to-help",
            ability="lee-opportunity-routing",
            organ="social-attention",
            sensory=["state/conversation_insight_inbox.jsonl", "state/conversation_insights.json", "state/owner_chat_signal_state.json"],
            semantic=["core/scripts/conversation_insight_tick.py", "core/scripts/lee_service_evidence_builder.py", "state/lee_service_help_evidence.json"],
            decision=["core/scripts/homeostatic_drive_arbiter.py", "core/scripts/resident_reflection.py", "state/lee_opportunity_review.json"],
            action=["core/action-state.json", "state/persona_deliberation_handoff.json"],
            learning=["MEMORY.md", "memory/2026-04-30.md", "core/learning-state.json"],
            safety=["core/homeostasis.json", "core/attention-state.json", "AGENTS.md", "HEARTBEAT.md"],
            runtime={
                "currentFocus": self_state.get("currentFocus"),
                "helpEvidenceRecommendation": help_evidence.get("recommendation", {}),
                "quietHours": homeostasis.get("quietHours", {}),
            },
        ),
        bind(
            "action-outcome-to-learning-backbone",
            ability="adaptive-learning",
            organ="cerebellum/procedural-memory",
            sensory=["core/action-state.json", "state/resident_reflection.json", "autonomy/experiment-log.jsonl"],
            semantic=["core/scripts/resident_reflection.py", "core/scripts/learning_update.py", "autonomy/output-evaluation.md"],
            decision=["core/procedural-memory.json", "core/scripts/action_ranker.py", "core/scripts/autonomy_upgrade_tick.py"],
            action=["core/scripts/resident_action.py", "core/scripts/persona_handoff_dispatch.py"],
            learning=["core/learning-state.json", "core/procedural-memory.json", "autonomy/continuity-state.json"],
            safety=common_safety,
            runtime={
                "recentIntentCount": len(recent_intents),
                "recentIntents": recent_intents,
                "lastMeaningfulProgressAt": self_state.get("lastMeaningfulProgressAt") or continuity.get("lastMeaningfulProgressAt"),
            },
        ),
    ]

    graph = {
        "timestamp": now_iso(),
        "status": "ok",
        "purpose": "Bind organs to perception, semantic interpretation, decision, action, learning, and safety paths so capabilities are not loose tools.",
        "policy": {
            "advisoryOnly": True,
            "multiLinkBinding": True,
            "noExternalWrite": True,
            "mainPersonaRequiredForBehaviorChanges": True,
        },
        "registryAbilityCount": len(abilities),
        "bindings": bindings,
        "currentRuntime": {
            "currentFocus": self_state.get("currentFocus"),
            "currentMode": self_state.get("currentMode"),
            "attentionMode": attention.get("mode") or attention.get("currentMode"),
            "recentSignals": recent_signals,
            "semanticObservations": as_list(semantic_signal.get("observations"))[-5:],
        },
        "recommendedNextConnector": "Feed state/organ_link_graph.json into signal_probe/action_ranker so organ evidence changes action scoring, not only documentation.",
    }
    save_json(OUTPUT, graph)

    # Lightweight view backrefs: make the link graph discoverable from body/perception/action without rewriting their main semantics.
    body.setdefault("organLinking", {})
    body["organLinking"].update({"enabled": True, "statePath": "state/organ_link_graph.json", "updatedAt": graph["timestamp"]})
    save_json(BODY_PATH, body)

    perception.setdefault("organLinking", {})
    perception["organLinking"].update({
        "enabled": True,
        "statePath": "state/organ_link_graph.json",
        "updatedAt": graph["timestamp"],
        "screenBindingLabels": screen_labels,
    })
    save_json(PERCEPTION_PATH, perception)

    action.setdefault("organLinking", {})
    action["organLinking"].update({"enabled": True, "statePath": "state/organ_link_graph.json", "updatedAt": graph["timestamp"]})
    save_json(ACTION_PATH, action)

    print(json.dumps({
        "ok": True,
        "output": str(OUTPUT.relative_to(ROOT)),
        "bindingCount": len(bindings),
        "recommendedNextConnector": graph["recommendedNextConnector"],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
