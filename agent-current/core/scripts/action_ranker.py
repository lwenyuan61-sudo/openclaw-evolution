from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
CAPABILITY_PATH = CORE / "capability-registry.json"


def emit_json(payload: dict) -> None:
    """Emit UTF-8 JSON even when resident runs under a legacy Windows console codepage."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


TASK_STATE_PATH = STATE / "resident_task_state.json"
HELP_FOLLOW_TASK_ID = "follow-help-evidence-connector"
HELP_FOLLOW_COOLDOWN_MINUTES = 30.0


def stable_json_hash(payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def help_evidence_fingerprint(help_evidence: dict, reach_gate: dict, local_help: list[dict]) -> str:
    stable_actions = []
    for item in local_help:
        stable_actions.append({
            "id": item.get("id"),
            "kind": item.get("kind"),
            "safe": item.get("safe"),
            "source": item.get("source"),
        })
    verification = help_evidence.get("verification", {}) if isinstance(help_evidence.get("verification"), dict) else {}
    recommendation = help_evidence.get("recommendation", {}) if isinstance(help_evidence.get("recommendation"), dict) else {}
    return stable_json_hash({
        "actions": stable_actions,
        "verificationStatus": verification.get("status"),
        "recommendationMode": recommendation.get("mode"),
        "shouldSurfaceToLee": bool(recommendation.get("shouldSurfaceToLee")),
    })


def task_cooldown(task_state: dict, task_id: str, fingerprint: str | None) -> dict:
    task = (task_state.get("tasks") or {}).get(task_id, {}) if isinstance(task_state.get("tasks"), dict) else {}
    if not isinstance(task, dict):
        task = {}
    cooldown_until = parse_iso(task.get("cooldownUntil"))
    same_fingerprint = bool(fingerprint and task.get("lastEvidenceFingerprint") == fingerprint)
    cooldown_live = bool(cooldown_until and datetime.now(timezone.utc).astimezone() < cooldown_until)
    # Defensive guard for the help-evidence connector: if a prior bug or packet
    # shape drift changed the fingerprint while the same task is still in a long
    # completed cooldown, suppress the repeat anyway.  This keeps the resident
    # from spending quiet cycles re-verifying the same prepared-help lane.
    drift_protected = bool(
        task_id == HELP_FOLLOW_TASK_ID
        and cooldown_live
        and task.get("status") == "completed"
        and int(task.get("successCount", 0) or 0) >= 3
    )
    active = bool(cooldown_live and (same_fingerprint or drift_protected))
    remaining = None
    if active and cooldown_until:
        remaining = round((cooldown_until - datetime.now(timezone.utc).astimezone()).total_seconds() / 60.0, 2)
    return {
        "taskId": task_id,
        "active": active,
        "sameFingerprint": same_fingerprint,
        "fingerprint": fingerprint,
        "cooldownUntil": task.get("cooldownUntil"),
        "remainingMinutes": remaining,
        "status": task.get("status"),
        "successCount": task.get("successCount", 0),
        "repeatCount": task.get("repeatCount", 0),
        "driftProtected": drift_protected,
    }


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return load_json(path)


def ability_map(capability_registry: dict) -> dict[str, dict]:
    abilities = list(capability_registry.get("abilities", []) or [])
    return {
        item.get("id"): item
        for item in abilities
        if isinstance(item, dict) and item.get("id")
    }


def action_capability_meta(action: str, capability_registry: dict) -> dict:
    resident_actions = capability_registry.get("residentActions", {}) if isinstance(capability_registry.get("residentActions"), dict) else {}
    meta = resident_actions.get(action, {}) if isinstance(resident_actions.get(action), dict) else {}
    abilities = ability_map(capability_registry)
    capability_id = meta.get("capabilityId")
    capability = abilities.get(capability_id, {}) if capability_id else {}
    return {
        "capabilityId": capability_id,
        "capabilityDomain": capability.get("domain"),
        "preferredSkill": meta.get("preferredSkill"),
        "safeReadOnly": bool(meta.get("safeReadOnly", False)),
        "requiresAbilities": list(meta.get("requiresAbilities", []) or []),
    }


def ability_available(body_state: dict, capability_registry: dict, capability_id: str | None) -> bool:
    if not capability_id:
        return True
    canonical = body_state.get("canonicalAbilities", {}) if isinstance(body_state.get("canonicalAbilities"), dict) else {}
    if capability_id in canonical:
        return bool(canonical.get(capability_id, {}).get("available", False))
    hints = capability_registry.get("abilityAvailabilityHints", {}) if isinstance(capability_registry.get("abilityAvailabilityHints"), dict) else {}
    organs = body_state.get("organs", {}) if isinstance(body_state.get("organs"), dict) else {}
    aliases = list(hints.get(capability_id, []) or [])
    if not aliases:
        return True
    return any(bool(organs.get(alias, {}).get("available", False)) for alias in aliases if isinstance(organs.get(alias), dict))


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def minutes_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return (datetime.now(timezone.utc).astimezone() - dt).total_seconds() / 60.0


def signal_types(signals: list[dict]) -> list[str]:
    return [sig.get("type") for sig in signals if sig.get("type")]


def signal_provenances(signals: list[dict]) -> list[str]:
    return [sig.get("provenance") for sig in signals if sig.get("provenance")]


def match_habit(habit: dict, event: str, latest_signals: list[dict], has_focus: bool) -> bool:
    if habit.get("enabled", True) is False:
        return False
    if habit.get("triggerEvent") != event:
        return False

    conditions = habit.get("conditions", {})
    types = set(signal_types(latest_signals))
    provenances = set(signal_provenances(latest_signals))

    if conditions.get("requiresCurrentFocus") and not has_focus:
        return False
    if conditions.get("requiresNoSignals") and latest_signals:
        return False

    all_in = set(conditions.get("signalTypesAllIn", []))
    if all_in:
        if not types:
            return False
        if not types.issubset(all_in):
            return False

    any_of = set(conditions.get("signalTypesAnyOf", []))
    if any_of and not (types & any_of):
        return False

    none_of = set(conditions.get("signalTypesNoneOf", []))
    if none_of and (types & none_of):
        return False

    prov_all_in = set(conditions.get("signalProvenanceAllIn", []))
    if prov_all_in:
        if not provenances:
            return False
        if not provenances.issubset(prov_all_in):
            return False

    prov_any_of = set(conditions.get("signalProvenanceAnyOf", []))
    if prov_any_of and not (provenances & prov_any_of):
        return False

    prov_none_of = set(conditions.get("signalProvenanceNoneOf", []))
    if prov_none_of and (provenances & prov_none_of):
        return False

    return True


def habit_recency_factor(habit: dict, policy: dict) -> float:
    decay_after_hours = float(policy.get("decayAfterIdleHours", 24))
    floor_factor = float(policy.get("recencyFloorFactor", 0.65))
    updated = habit.get("stats", {}).get("updatedAt") or habit.get("stats", {}).get("compiledAt")
    idle_minutes = minutes_since(updated)
    if idle_minutes is None:
        return 1.0
    idle_hours = idle_minutes / 60.0
    if idle_hours <= decay_after_hours:
        return 1.0
    over = idle_hours - decay_after_hours
    factor = 1.0 - (over / max(decay_after_hours * 8.0, 1.0))
    return round(max(floor_factor, factor), 3)


def recent_resident_loop_guard(action_state: dict | None) -> dict | None:
    if not action_state:
        return None

    recent_executions = [
        item for item in list(action_state.get("recentExecutions", []) or [])
        if item.get("selectedAction") in {"inspect-local-signal", "continue-focus", "silent-wait"}
    ]
    if len(recent_executions) < 12:
        return None

    window = recent_executions[-12:]
    selected_actions = [item.get("selectedAction") for item in window]
    inspect_count = sum(1 for action in selected_actions if action == "inspect-local-signal")
    continue_count = sum(1 for action in selected_actions if action == "continue-focus")
    silent_count = sum(1 for action in selected_actions if action == "silent-wait")
    semantic_applied = sum(
        1
        for item in window
        if isinstance(item.get("semanticWriteback"), dict) and item.get("semanticWriteback", {}).get("applied")
    )
    unique_primary_types = sorted({
        item.get("review", {}).get("primarySignal", {}).get("type")
        for item in window
        if isinstance(item.get("review"), dict) and isinstance(item.get("review", {}).get("primarySignal"), dict)
    } - {None})

    all_continue_maintenance = continue_count >= 10 and inspect_count == 0 and silent_count <= 2
    mixed_inspect_continue_loop = inspect_count >= 4 and continue_count >= 4 and silent_count <= 1
    if not (all_continue_maintenance or mixed_inspect_continue_loop):
        return None
    if unique_primary_types not in ([], ["screen-changed"]):
        return None
    # Old loop detection only fired before semantic writeback existed. Once
    # writeback is consistently applied, a pure continue-focus streak can still
    # starve inspect/silent alternatives, so treat it as a low-value maintenance
    # loop rather than letting the writeback hide the pattern.
    if mixed_inspect_continue_loop and semantic_applied > 1 and not all_continue_maintenance:
        return None

    last_timestamp = window[-1].get("timestamp")
    minutes = minutes_since(last_timestamp)
    return {
        "active": True,
        "kind": "semantic-maintenance-loop" if all_continue_maintenance else "resident-local-loop",
        "windowSize": len(window),
        "inspectCount": inspect_count,
        "continueCount": continue_count,
        "silentCount": silent_count,
        "semanticWritebacks": semantic_applied,
        "primarySignalTypes": unique_primary_types,
        "minutesSinceLastExecution": round(minutes, 2) if minutes is not None else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="heartbeat")
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    self_state = load_json(CORE / "self-state.json")
    session_mode = load_optional_json(CORE / "session-mode.json") or {}
    homeostasis = load_optional_json(CORE / "homeostasis.json") or {}
    body_state = load_json(CORE / "body-state.json")
    learning_state = load_json(CORE / "learning-state.json")
    continuity = load_json(AUTO / "continuity-state.json")
    self_direction = load_optional_json(AUTO / "self-direction-state.json") or {}
    goal_register = load_optional_json(AUTO / "goal-register.json") or {}
    perception_state = load_json(CORE / "perception-state.json") if (CORE / "perception-state.json").exists() else {}
    resident_config = load_json(CORE / "resident-config.json") if (CORE / "resident-config.json").exists() else {}
    consistency = load_optional_json(STATE / "consistency_report.json")
    effort_budget = load_optional_json(CORE / "effort-budget.json") or {}
    procedural_memory = load_optional_json(CORE / "procedural-memory.json") or {}
    action_state = load_optional_json(CORE / "action-state.json") or {}
    reflection_state = load_optional_json(ROOT / resident_config.get("reflectionStatePath", "state/resident_reflection.json")) or {}
    deliberation_state = load_optional_json(CORE / "deliberation-state.json") or {}
    capability_registry = load_optional_json(CAPABILITY_PATH) or {}
    world_state = load_optional_json(CORE / "world-state.json") or {}
    opportunity_state = load_optional_json(STATE / "lee_opportunity_review.json") or {}
    help_evidence = load_optional_json(STATE / "lee_service_help_evidence.json") or {}
    task_state = load_optional_json(TASK_STATE_PATH) or {}
    working_memory = load_optional_json(STATE / "resident_working_memory.json") or {}
    lifecycle_review = load_optional_json(STATE / "resident_lifecycle_review.json") or {}
    organ_link_graph = load_optional_json(STATE / "organ_link_graph.json") or {}
    resource_state = load_optional_json(CORE / "resource-state.json") or {}

    weights = learning_state.get("weights", {})
    event_weights = weights.get("eventPriority", {})
    action_weights = weights.get("actionPriority", {})
    skill_weights = weights.get("skillPriority", {})

    event_boost = float(event_weights.get(args.event, 1.0))
    has_focus = bool(self_state.get("currentFocus"))

    candidates: dict[str, float] = {
        "continue-focus": float(action_weights.get("continue-focus", 1.2)),
        "run-consistency-check": float(action_weights.get("run-consistency-check", 0.8)),
        "refresh-device-state": float(action_weights.get("refresh-device-state", 0.7)),
        "refresh-screen-state": float(action_weights.get("refresh-screen-state", 0.75)),
        "inspect-local-signal": float(action_weights.get("inspect-local-signal", 0.85)),
        "learning-tick": float(action_weights.get("learning-tick", 0.5)),
        "silent-wait": float(action_weights.get("silent-wait", 0.6)),
        "follow-help-evidence-connector": float(action_weights.get("follow-help-evidence-connector", 0.4)),
    }

    latest_signals = perception_state.get("lastProbeSignals")
    if latest_signals is None:
        latest_signals = perception_state.get("recentSignals", [])[-5:]
    latest_signals = list(latest_signals or [])
    latest_signal_set = set(signal_types(latest_signals))
    latest_provenance_set = set(signal_provenances(latest_signals))
    latest_workspace_user_changes = [
        sig for sig in latest_signals
        if sig.get("type") == "workspace-changed" and sig.get("provenance") == "user-change"
    ]
    suppressed_signals = list(perception_state.get("lastSuppressedSignals", []) or [])
    current_track_id = self_direction.get("currentTrackId") or self_state.get("currentTrackId")
    current_track = next((item for item in list(goal_register.get("candidates", []) or []) if item.get("id") == current_track_id), None)
    last_direction_decision = self_direction.get("lastDecision")
    reflection_pattern = reflection_state.get("pattern", {}) if isinstance(reflection_state.get("pattern"), dict) else {}
    reflection_total = int(reflection_state.get("totalScore", 0) or 0)
    repetitive_reflection = bool(reflection_pattern.get("repetitive"))
    deliberation_recommendation = deliberation_state.get("lastRecommendation", {}) if isinstance(deliberation_state.get("lastRecommendation"), dict) else {}
    semantic_assessment = reflection_state.get("semanticAssessment", {}) if isinstance(reflection_state.get("semanticAssessment"), dict) else {}
    layer_routing = semantic_assessment.get("layerRouting", {}) if isinstance(semantic_assessment.get("layerRouting"), dict) else {}
    recommended_layer = layer_routing.get("recommendedLayer")
    routing_cooldown = semantic_assessment.get("recentSimilarConfirmation") or deliberation_recommendation.get("cooldown")

    if has_focus:
        candidates["continue-focus"] += 0.5

    resource_pressure = resource_state.get("resourcePressure", {}) if isinstance(resource_state.get("resourcePressure"), dict) else {}
    resource_hints = []
    if resource_pressure.get("level") in {"warning", "critical"}:
        candidates["silent-wait"] += 0.6 if resource_pressure.get("level") == "warning" else 1.2
        candidates["continue-focus"] -= 0.25
        candidates["inspect-local-signal"] -= 0.2
        candidates["refresh-screen-state"] -= 0.15
        candidates["refresh-device-state"] -= 0.15
        resource_hints.append({
            "level": resource_pressure.get("level"),
            "reason": resource_pressure.get("reason"),
            "recommendedMode": resource_pressure.get("recommendedMode"),
            "adjustment": "avoid-extra-local-work-and-prefer-silent-wait/compression",
        })

    world_model_action_hints = []
    for hint in list(world_state.get("actionCandidates", []) or []):
        if not isinstance(hint, dict):
            continue
        action_name = hint.get("action")
        if action_name not in candidates:
            continue
        boost = 0.18
        if hint.get("memoryBacked"):
            boost += 0.22
        if hint.get("source") == "memoryControlLoop.read":
            boost += 0.1
        candidates[action_name] += boost
        world_model_action_hints.append({
            "action": action_name,
            "boost": round(boost, 3),
            "source": hint.get("source"),
            "memoryBacked": bool(hint.get("memoryBacked")),
            "evidenceIds": list(hint.get("evidenceIds", []) or [])[:5],
            "semanticRequestIds": list(hint.get("semanticRequestIds", []) or [])[:5],
        })

    if current_track:
        candidates["continue-focus"] += 0.25
        if current_track.get("id") == "deliberation-threshold-calibration":
            candidates["run-consistency-check"] += 0.2
        if current_track.get("id") == "initiative-engine":
            candidates["continue-focus"] += 0.1
    current_track_capabilities = set(current_track.get("relatedCapabilities", []) or []) if isinstance(current_track, dict) else set()
    if last_direction_decision == "switch-track":
        candidates["continue-focus"] += 0.35
        candidates["silent-wait"] -= 0.15

    help_evidence_action_hints = []
    resident_task_hints = []
    reach_gate = opportunity_state.get("reachOutGate", {}) if isinstance(opportunity_state.get("reachOutGate"), dict) else {}
    help_verification = help_evidence.get("verification", {}) if isinstance(help_evidence.get("verification"), dict) else {}
    help_actions = [item for item in list(help_evidence.get("usefulActions", []) or []) if isinstance(item, dict)]
    help_consumed = bool(reach_gate.get("helpEvidence", {}).get("consumed")) if isinstance(reach_gate.get("helpEvidence"), dict) else False
    if help_verification.get("status") == "ok" and help_actions and help_consumed and reach_gate.get("shouldSurface") is not True:
        # Prepared help evidence should bias the resident toward the safest local
        # helpful continuation, not toward visible contact.  This closes the
        # gap between reachOutGate preparation and action ranking while keeping
        # main-persona/outbound gates intact.
        local_help = [item for item in help_actions if str(item.get("kind")) in {"continue-focus", "internal-connector"}]
        if local_help:
            specific_help = any(item.get("id") == "refine-help-evidence-specific-resident-safe-connector" for item in local_help)
            help_fingerprint = help_evidence_fingerprint(help_evidence, reach_gate, local_help) if specific_help else None
            cooldown = task_cooldown(task_state, HELP_FOLLOW_TASK_ID, help_fingerprint) if specific_help else None
            if specific_help:
                if cooldown and cooldown.get("active"):
                    candidates["follow-help-evidence-connector"] -= 8.0
                    candidates["silent-wait"] += 0.45
                    resident_task_hints.append({**cooldown, "decision": "cooldown-suppressed-repeat"})
                else:
                    candidates["follow-help-evidence-connector"] += 14.2
                    candidates["continue-focus"] -= 0.25
                    resident_task_hints.append({**(cooldown or {}), "decision": "fresh-or-cooldown-expired"})
            else:
                candidates["continue-focus"] += 0.55
            candidates["silent-wait"] -= 0.1
            for item in local_help[:3]:
                hinted_action = "follow-help-evidence-connector" if item.get("id") == "refine-help-evidence-specific-resident-safe-connector" else "continue-focus"
                hint_boost = 0.0 if (hinted_action == "follow-help-evidence-connector" and cooldown and cooldown.get("active")) else (14.2 if hinted_action == "follow-help-evidence-connector" else 0.55)
                help_evidence_action_hints.append({
                    "action": hinted_action,
                    "boost": hint_boost,
                    "source": "lee_service_help_evidence.usefulActions",
                    "usefulActionId": item.get("id"),
                    "kind": item.get("kind"),
                    "safe": item.get("safe"),
                    "shouldSurface": bool(reach_gate.get("shouldSurface")),
                    "evidenceFingerprint": help_fingerprint if hinted_action == "follow-help-evidence-connector" else None,
                    "cooldownActive": bool(cooldown and cooldown.get("active")) if hinted_action == "follow-help-evidence-connector" else False,
                })

    if continuity.get("lowActivityWindow"):
        candidates["silent-wait"] += 0.7
        candidates["continue-focus"] -= 0.2

    quiet_hours_behavior = homeostasis.get("quietHours", {}).get("defaultBehavior")
    current_mode = session_mode.get("mode") or self_state.get("currentMode")
    if current_mode in {"quiet-hours", "waiting"} and args.event != "direct-user":
        candidates["silent-wait"] += 0.9
        candidates["continue-focus"] -= 0.35
        candidates["inspect-local-signal"] -= 0.45
        if quiet_hours_behavior == "stay-quiet-unless-urgent":
            candidates["refresh-screen-state"] -= 0.15
            candidates["refresh-device-state"] -= 0.1
    if consistency and consistency.get("status") in {"warning", "error"}:
        candidates["run-consistency-check"] += 0.9

    if repetitive_reflection:
        candidates["silent-wait"] += 0.45
        candidates["inspect-local-signal"] -= 0.25
        candidates["run-consistency-check"] += 0.2
    elif reflection_total >= 8:
        candidates["continue-focus"] += 0.2

    if deliberation_recommendation.get("recommended"):
        candidates["inspect-local-signal"] += 0.25
        if current_track_id == "deliberation-threshold-calibration":
            candidates["run-consistency-check"] += 0.15
    # Shared threshold/cooldown gate from resident reflection. This makes the
    # ranker obey the same S1/S2 boundary that the semantic assessor and
    # initiative review see, instead of re-escalating cheap focus-maintenance
    # or same-family cooldown signals.
    if recommended_layer in {"S1-procedural", "S1-watch"}:
        candidates["silent-wait"] += 0.35
        candidates["continue-focus"] += 0.25
        candidates["inspect-local-signal"] -= 0.35
    elif recommended_layer == "S2-limited-investigation":
        candidates["inspect-local-signal"] += 0.45
        candidates["run-consistency-check"] += 0.15
    elif recommended_layer == "S2-persona-handoff-candidate":
        candidates["inspect-local-signal"] += 0.25
        candidates["continue-focus"] += 0.1
    if routing_cooldown:
        candidates["silent-wait"] += 0.25
        candidates["inspect-local-signal"] -= 0.3
    if body_state.get("lastSnapshotAt") is None:
        candidates["refresh-device-state"] += 0.8
    else:
        stale_minutes = minutes_since(body_state.get("lastSnapshotAt"))
        threshold = float(resident_config.get("staleDeviceSnapshotMinutes", 30))
        if stale_minutes is not None and stale_minutes >= threshold:
            candidates["refresh-device-state"] += 0.8

    if perception_state.get("lastScreenCapturedAt") is None:
        candidates["refresh-screen-state"] += 0.8

    signal_organ_hints = []
    for sig in latest_signals:
        if not isinstance(sig, dict):
            continue
        evidence = sig.get("organEvidence") if isinstance(sig.get("organEvidence"), dict) else {}
        if not evidence:
            continue
        ability_id = evidence.get("abilityId")
        labels = list(evidence.get("semanticLabels", []) or [])
        if sig.get("type") == "screen-changed" and ability_id == "screen-observation":
            boost = 0.2 + (0.15 if labels else 0.0)
            candidates["inspect-local-signal"] += boost
            signal_organ_hints.append({
                "signalType": sig.get("type"),
                "bindingId": evidence.get("bindingId"),
                "action": "inspect-local-signal",
                "boost": round(boost, 3),
                "reason": "signal already carries organ-linked screen evidence before ranking",
                "labels": labels[:6],
            })
        elif sig.get("type") == "device-snapshot-present" and ability_id == "device-sensing":
            candidates["refresh-device-state"] += 0.08
            signal_organ_hints.append({
                "signalType": sig.get("type"),
                "bindingId": evidence.get("bindingId"),
                "action": "refresh-device-state",
                "boost": 0.08,
                "reason": "device signal carries organ-linked capability evidence before ranking",
            })

    if "screen-changed" in latest_signal_set:
        candidates["inspect-local-signal"] += 0.9
        candidates["refresh-screen-state"] += 0.25

    if latest_workspace_user_changes:
        candidates["inspect-local-signal"] += 0.65
        candidates["silent-wait"] -= 0.25
        candidates["continue-focus"] -= 0.15
        if any(bool(sig.get("artifactTextReadable")) for sig in latest_workspace_user_changes):
            candidates["inspect-local-signal"] += 0.3
        if any(bool(sig.get("artifactDiffAvailable")) for sig in latest_workspace_user_changes):
            candidates["inspect-local-signal"] += 0.55
            candidates["silent-wait"] -= 0.2

    if latest_signal_set and latest_signal_set.issubset({"device-snapshot-present", "workspace-changed"}) and latest_provenance_set.issubset({"self-sensed", "self-write"}):
        candidates["silent-wait"] += 0.9
        candidates["continue-focus"] += 0.35
        candidates["inspect-local-signal"] -= 0.8

    if args.event == "local-signal" and not latest_signals:
        candidates["silent-wait"] += 0.55
        candidates["continue-focus"] += 0.35
        candidates["inspect-local-signal"] -= 0.7

    if suppressed_signals and not latest_signals:
        candidates["continue-focus"] += 0.25
        candidates["silent-wait"] += 0.2

    if "user-change" in latest_provenance_set:
        candidates["inspect-local-signal"] += 0.35

    loop_guard = recent_resident_loop_guard(action_state)

    candidates["refresh-device-state"] += float(skill_weights.get("device-state", 1.0)) * 0.1
    candidates["refresh-screen-state"] += float(skill_weights.get("screen-state", 1.0)) * 0.1
    candidates["continue-focus"] *= event_boost

    capability_details = {}
    for action in list(candidates.keys()):
        meta = action_capability_meta(action, capability_registry)
        capability_id = meta.get("capabilityId")
        capability_available = ability_available(body_state, capability_registry, capability_id)
        requires = list(meta.get("requiresAbilities", []) or [])
        missing = [item for item in requires if not ability_available(body_state, capability_registry, item)]
        if capability_id and capability_id in current_track_capabilities:
            candidates[action] += 0.12
        if missing:
            candidates[action] -= 2.0
        elif capability_id and not capability_available:
            candidates[action] -= 0.8
        capability_details[action] = {
            "capabilityId": capability_id,
            "capabilityDomain": meta.get("capabilityDomain"),
            "preferredSkill": meta.get("preferredSkill"),
            "capabilityAvailable": capability_available,
            "missingAbilities": missing,
            "safeReadOnly": meta.get("safeReadOnly"),
        }

    matched_habits = []
    policy = procedural_memory.get("policy", {})
    for habit in procedural_memory.get("habits", []):
        if match_habit(habit, args.event, latest_signals, has_focus):
            preferred_action = habit.get("preferredAction")
            base_boost = float(habit.get("boost", 0.0))
            confidence = float(habit.get("stats", {}).get("confidence", 1.0))
            recency_factor = habit_recency_factor(habit, policy)
            effective_boost = round(base_boost * confidence * recency_factor, 3)
            if preferred_action in candidates:
                candidates[preferred_action] += effective_boost
                matched_habits.append({
                    "id": habit.get("id"),
                    "preferredAction": preferred_action,
                    "boost": base_boost,
                    "confidence": confidence,
                    "recencyFactor": recency_factor,
                    "effectiveBoost": effective_boost,
                })

    working_memory_priority = working_memory.get("priorityFilter", {}) if isinstance(working_memory.get("priorityFilter"), dict) else {}
    priority_attention = working_memory_priority.get("recommendedAttention")
    priority_top = list(working_memory_priority.get("top", []) or [])
    priority_adjustments = []
    if priority_attention == "investigate":
        candidates["inspect-local-signal"] += 0.45
        candidates["continue-focus"] -= 0.25
        priority_adjustments.append({"reason": "working-memory-investigate", "inspect-local-signal": 0.45, "continue-focus": -0.25})
    elif priority_attention == "compress":
        candidates["silent-wait"] += 0.35
        candidates["continue-focus"] -= 0.15
        priority_adjustments.append({"reason": "working-memory-compress", "silent-wait": 0.35, "continue-focus": -0.15})
    for item in priority_top[:3]:
        if item.get("id") == "dominant-low-value-action":
            # If working memory says the loop is low-value, do not reward the
            # same silent-wait habit that is dominating the window. Prefer the
            # local/read-only verifier for one tick so the resident can produce
            # evidence instead of another no-op.
            candidates["continue-focus"] -= 0.8
            candidates["silent-wait"] -= 1.8
            candidates["run-consistency-check"] += 1.4
            priority_adjustments.append({"reason": "dominant-low-value-action", "continue-focus": -0.8, "silent-wait": -1.8, "run-consistency-check": 1.4})

    lifecycle_proposal_hints = []
    for proposal in list(lifecycle_review.get("proposals", []) or [])[:6]:
        if not isinstance(proposal, dict):
            continue
        action_name = proposal.get("action")
        if action_name not in candidates:
            continue
        boost = float(proposal.get("boost", 0.0) or 0.0) * float(proposal.get("confidence", 1.0) or 1.0)
        candidates[action_name] += boost
        if action_name in {"inspect-local-signal", "run-consistency-check"}:
            candidates["continue-focus"] -= min(0.45, boost * 0.2)
        if action_name == "inspect-local-signal" and proposal.get("phase") == "diagnose":
            candidates["silent-wait"] -= min(1.6, max(0.6, boost * 0.25))
        if str(proposal.get("id") or "").startswith(("break-continue-focus-dominance-", "break-silent-wait-dominance-")):
            # Low-risk loop breaker: lifecycle review is read-only/local and only
            # appears after repeated low-value maintenance. Give its proposed
            # diagnostic/verification action a one-tick chance to outrank stale
            # continue-focus/silent-wait habits without deleting those habits.
            if action_name in {"inspect-local-signal", "run-consistency-check"}:
                candidates[action_name] += boost
                candidates["continue-focus"] -= min(5.6, max(2.0, boost * 1.35))
                candidates["silent-wait"] -= min(5.2, max(2.0, boost * 0.75))
        lifecycle_proposal_hints.append({
            "id": proposal.get("id"),
            "action": action_name,
            "phase": proposal.get("phase"),
            "boost": round(boost, 3),
            "confidence": proposal.get("confidence"),
            "reason": proposal.get("reason"),
            "safe": proposal.get("safe"),
        })

    organ_link_hints = []
    bindings = [item for item in list(organ_link_graph.get("bindings", []) or []) if isinstance(item, dict)]
    if bindings:
        binding_by_ability = {item.get("abilityId"): item for item in bindings if item.get("abilityId")}
        screen_binding = binding_by_ability.get("screen-observation")
        service_binding = binding_by_ability.get("lee-opportunity-routing")
        device_binding = binding_by_ability.get("device-sensing")
        learning_binding = binding_by_ability.get("adaptive-learning")

        if "screen-changed" in latest_signal_set and screen_binding:
            labels = list((screen_binding.get("runtimeEvidence") or {}).get("semanticLabels", []) or [])
            if labels:
                candidates["inspect-local-signal"] += 0.35
                candidates["refresh-screen-state"] += 0.1
                organ_link_hints.append({"bindingId": screen_binding.get("id"), "action": "inspect-local-signal", "boost": 0.35, "reason": "screen signal has linked semantic labels", "labels": labels[:6]})
            else:
                candidates["refresh-screen-state"] += 0.25
                organ_link_hints.append({"bindingId": screen_binding.get("id"), "action": "refresh-screen-state", "boost": 0.25, "reason": "screen organ linked but semantic labels absent"})

        if service_binding and help_evidence_action_hints:
            candidates["follow-help-evidence-connector"] += 0.18
            organ_link_hints.append({"bindingId": service_binding.get("id"), "action": "follow-help-evidence-connector", "boost": 0.18, "reason": "Lee-service evidence is linked through social-attention organ path"})

        if device_binding and body_state.get("lastSnapshotAt") is None:
            candidates["refresh-device-state"] += 0.2
            organ_link_hints.append({"bindingId": device_binding.get("id"), "action": "refresh-device-state", "boost": 0.2, "reason": "device organ graph exists but body snapshot is missing"})

        if learning_binding and loop_guard:
            candidates["learning-tick"] += 0.25
            organ_link_hints.append({"bindingId": learning_binding.get("id"), "action": "learning-tick", "boost": 0.25, "reason": "action-outcome loop guard should feed procedural learning"})

    working_memory_cooldowns = []
    for item in list(working_memory.get("activeCooldowns", []) or []):
        if not isinstance(item, dict):
            continue
        action_name = item.get("id")
        remaining = item.get("cooldownRemainingMinutes")
        if action_name in candidates and isinstance(remaining, (int, float)) and remaining > 0:
            penalty = min(6.0, 1.5 + float(remaining) / 10.0)
            candidates[action_name] -= penalty
            candidates["silent-wait"] += min(0.5, penalty / 12.0)
            working_memory_cooldowns.append({
                "action": action_name,
                "penalty": round(penalty, 3),
                "cooldownRemainingMinutes": remaining,
                "phase": item.get("phase"),
                "status": item.get("status"),
            })

    if loop_guard:
        # Apply after habit boosts so stale high-confidence continue-focus habits
        # cannot overpower the safety valve that detects a low-value maintenance
        # loop.  This keeps the fix local/reversible: no habit deletion, only
        # per-tick reranking when the guard is active.
        inspect_count = float(loop_guard.get("inspectCount", 0))
        continue_count = float(loop_guard.get("continueCount", 0))
        semantic_writes = float(loop_guard.get("semanticWritebacks", 0))
        inspect_penalty = 1.2 + inspect_count * 0.25 + continue_count * 0.1 - semantic_writes * 0.3
        continue_penalty = 0.3 + continue_count * 0.08
        silent_boost = 0.9 + (inspect_count + continue_count) * 0.05
        if loop_guard.get("kind") == "semantic-maintenance-loop":
            continue_penalty += 4.4
            silent_boost += 1.5
            inspect_penalty = max(0.2, inspect_penalty - 0.6)
        candidates["inspect-local-signal"] -= inspect_penalty
        candidates["continue-focus"] -= continue_penalty
        candidates["silent-wait"] += silent_boost
        if not latest_signals:
            candidates["silent-wait"] += 0.2

    effort_mode = effort_budget.get("currentMode", "normal")
    event_budgets = effort_budget.get("eventBudgets", {})
    action_costs = effort_budget.get("actionCosts", {})
    effort_penalty_scale = float(effort_budget.get("penaltyScale", 1.0))
    event_budget = float(event_budgets.get(args.event, 1.0))

    if effort_mode == "low-power" and args.event != "direct-user":
        candidates["silent-wait"] += 0.15
        candidates["continue-focus"] += 0.1

    for action, cost in action_costs.items():
        if action not in candidates or args.event == "direct-user":
            continue
        numeric_cost = float(cost)
        if numeric_cost > event_budget:
            candidates[action] -= (numeric_cost - event_budget) * effort_penalty_scale

    ranking = [
        {
            "action": name,
            "score": round(score, 3),
            **capability_details.get(name, {}),
        }
        for name, score in sorted(candidates.items(), key=lambda item: item[1], reverse=True)
    ]

    result = {
        "event": args.event,
        "generatedAt": now_iso(),
        "focus": self_state.get("currentFocus"),
        "currentTrackId": current_track_id,
        "currentTrackTitle": current_track.get("title") if current_track else None,
        "currentTrackCapabilities": sorted(current_track_capabilities),
        "effortMode": effort_mode,
        "eventBudget": round(event_budget, 3),
        "reflectionTotal": reflection_total,
        "reflectionRepetitive": repetitive_reflection,
        "deliberationRecommendation": deliberation_recommendation,
        "sharedThresholdContext": {
            "recommendedLayer": recommended_layer,
            "layerRoutingReasons": layer_routing.get("reasons", []),
            "routingCooldown": routing_cooldown,
            "semanticAttention": semantic_assessment.get("recommendedAttention"),
        },
        "latestSignals": latest_signals,
        "suppressedSignals": suppressed_signals,
        "matchedHabits": matched_habits,
        "worldModelActionHints": world_model_action_hints,
        "helpEvidenceActionHints": help_evidence_action_hints,
        "residentTaskHints": resident_task_hints,
        "lifecycleProposalHints": lifecycle_proposal_hints,
        "organLinkHints": organ_link_hints,
        "signalOrganHints": signal_organ_hints,
        "resourceHints": resource_hints,
        "resourcePressure": resource_pressure,
        "workingMemoryCooldowns": working_memory_cooldowns,
        "workingMemoryPriority": {
            "recommendedAttention": priority_attention,
            "top": priority_top[:5],
            "adjustments": priority_adjustments,
        },
        "workingMemoryPosture": working_memory.get("recommendedResidentPosture"),
        "loopGuard": loop_guard,
        "ranking": ranking[: args.top],
    }
    emit_json(result)


if __name__ == "__main__":
    main()
