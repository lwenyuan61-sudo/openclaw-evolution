from __future__ import annotations

import json
import sys
from datetime import datetime, time, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

try:
    from .opportunity_semantic_assessor import assess_opportunity_semantics
except ImportError:
    from opportunity_semantic_assessor import assess_opportunity_semantics

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
ACTION_STATE_PATH = CORE / "action-state.json"
SELF_STATE_PATH = CORE / "self-state.json"
SESSION_MODE_PATH = CORE / "session-mode.json"
HOMEOSTASIS_PATH = CORE / "homeostasis.json"
CONTINUITY_PATH = AUTO / "continuity-state.json"
SELF_DIRECTION_PATH = AUTO / "self-direction-state.json"
DELIBERATION_PATH = CORE / "deliberation-state.json"
ATTENTION_PATH = CORE / "attention-state.json"
RESIDENT_CONFIG_PATH = CORE / "resident-config.json"
DEFAULT_REFLECTION_PATH = STATE / "resident_reflection.json"
DEFAULT_OPPORTUNITY_PATH = STATE / "lee_opportunity_review.json"
CAPABILITY_PATH = CORE / "capability-registry.json"
PROCEDURAL_PATH = CORE / "procedural-memory.json"
SCREEN_STATE_PATH = STATE / "screen_state.json"
UPGRADE_PATH = AUTO / "upgrade-state.json"
LEE_SERVICE_HELP_EVIDENCE_PATH = STATE / "lee_service_help_evidence.json"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_capability_registry() -> dict:
    return load_optional_json(CAPABILITY_PATH)


def matching_deliberation_pattern(procedural_memory: dict, latest: dict, total: int) -> dict | None:
    review = latest.get("review", {}) if isinstance(latest.get("review"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else {}
    if not primary:
        return None

    patterns = list(procedural_memory.get("deliberationPatterns", []) or [])
    capability_id = latest.get("capabilityId")
    capability_domain = latest.get("capabilityDomain")
    for pattern in patterns:
        conditions = pattern.get("conditions", {}) if isinstance(pattern.get("conditions"), dict) else {}
        signal_types = set(conditions.get("signalTypesAnyOf", []))
        provenances = set(conditions.get("signalProvenanceAnyOf", []))
        if signal_types and primary.get("type") not in signal_types:
            continue
        if provenances and primary.get("provenance") not in provenances:
            continue
        if conditions.get("latestCapabilityId") and conditions.get("latestCapabilityId") != capability_id:
            continue
        if conditions.get("latestCapabilityDomain") and conditions.get("latestCapabilityDomain") != capability_domain:
            continue
        if total < int(conditions.get("minValueScore", 0) or 0):
            continue
        return pattern
    return None


def parse_hhmm(value: str | None) -> time | None:
    if not value or ":" not in value:
        return None
    hour, minute = value.split(":", 1)
    try:
        return time(hour=int(hour), minute=int(minute))
    except Exception:
        return None


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
    return (now() - dt).total_seconds() / 60.0


def workspace_signal_identity(signal: dict) -> tuple:
    return (
        signal.get("path"),
        signal.get("oldContentHash"),
        signal.get("newContentHash"),
        signal.get("artifactKind"),
    )


def same_signal_family(a: dict, b: dict) -> bool:
    if not isinstance(a, dict) or not isinstance(b, dict):
        return False
    if a.get("type") != b.get("type") or a.get("provenance") != b.get("provenance"):
        return False
    if a.get("type") == "workspace-changed":
        # Artifact identity must include the file and content transition, not just
        # the broad signal family, otherwise distinct text changes get suppressed.
        return workspace_signal_identity(a) == workspace_signal_identity(b)
    return True


def signal_is_external(primary: dict) -> bool:
    if not isinstance(primary, dict):
        return False
    return primary.get("provenance") not in {None, "self-write", "self-sensed"}


def deliberation_cooldown(deliberation_state: dict, primary: dict, compiled_pattern: dict | None) -> dict | None:
    if not primary:
        return None
    policy = deliberation_state.get("episodePolicy", {}) if isinstance(deliberation_state.get("episodePolicy"), dict) else {}
    cooldown_minutes = float(policy.get("sameSignalCooldownMinutes", 10) or 10)
    if cooldown_minutes <= 0:
        return None

    last_episode = deliberation_state.get("lastEpisode", {}) if isinstance(deliberation_state.get("lastEpisode"), dict) else {}
    last_primary = last_episode.get("primarySignal", {}) if isinstance(last_episode.get("primarySignal"), dict) else {}
    if not last_primary or not same_signal_family(last_primary, primary):
        return None

    elapsed = minutes_since(last_episode.get("endedAt"))
    if elapsed is None or elapsed >= cooldown_minutes:
        return None

    return {
        "active": True,
        "elapsedMinutes": round(elapsed, 3),
        "cooldownMinutes": cooldown_minutes,
        "lastEpisodeId": last_episode.get("episodeId"),
        "lastOutcome": last_episode.get("outcome"),
        "compiledPatternId": compiled_pattern.get("id") if compiled_pattern else None,
    }


def in_quiet_hours(homeostasis: dict, current: datetime) -> bool:
    quiet = homeostasis.get("quietHours", {})
    start = parse_hhmm(quiet.get("start"))
    end = parse_hhmm(quiet.get("end"))
    if not start or not end:
        return False
    current_t = current.timetz().replace(tzinfo=None)
    if start <= end:
        return start <= current_t < end
    return current_t >= start or current_t < end


def trim_list(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def recent_loop_pattern(action_state: dict) -> dict:
    recent = [
        item for item in list(action_state.get("recentExecutions", []) or [])
        if item.get("selectedAction") in {"inspect-local-signal", "continue-focus", "silent-wait"}
    ]
    window = recent[-12:]
    inspect_count = sum(1 for item in window if item.get("selectedAction") == "inspect-local-signal")
    continue_count = sum(1 for item in window if item.get("selectedAction") == "continue-focus")
    silent_count = sum(1 for item in window if item.get("selectedAction") == "silent-wait")
    semantic_writes = sum(
        1
        for item in window
        if isinstance(item.get("semanticWriteback"), dict) and item.get("semanticWriteback", {}).get("applied")
    )
    repetitive = (
        len(window) >= 8
        and inspect_count >= 3
        and continue_count >= 3
        and silent_count == 0
        and semantic_writes <= 1
    )
    return {
        "windowSize": len(window),
        "inspectCount": inspect_count,
        "continueCount": continue_count,
        "silentCount": silent_count,
        "semanticWritebacks": semantic_writes,
        "repetitive": repetitive,
    }


def classify_value(execution: dict, pattern: dict) -> tuple[str, dict, int]:
    action = execution.get("selectedAction")
    semantic = execution.get("semanticWriteback", {}) if isinstance(execution.get("semanticWriteback"), dict) else {}
    verification = execution.get("verification", {}) if isinstance(execution.get("verification"), dict) else {}
    verification_parsed = verification.get("parsed", {}) if isinstance(verification.get("parsed"), dict) else {}

    scores = {
        "artifact": 0,
        "continuity": 0,
        "value": 0,
        "efficiency": 0,
        "agency": 0,
    }
    category = "self-maintenance-only"

    if semantic.get("applied"):
        scores.update({"artifact": 2, "continuity": 2, "value": 2, "efficiency": 2, "agency": 2})
        category = "capability-value"
    elif action == "inspect-local-signal" and verification_parsed.get("status") == "ok":
        scores["artifact"] = 1
        scores["continuity"] = 2
        scores["agency"] = 2
        if pattern.get("repetitive"):
            scores["value"] = 0
            scores["efficiency"] = 0
            category = "self-maintenance-only"
        else:
            scores["value"] = 1
            scores["efficiency"] = 1
            category = "capability-value"
    elif action in {"continue-focus", "silent-wait"}:
        scores["artifact"] = 1
        scores["continuity"] = 2
        scores["agency"] = 1
        if pattern.get("repetitive"):
            scores["value"] = 1 if action == "silent-wait" else 0
            scores["efficiency"] = 2 if action == "silent-wait" else 0
            category = "capability-value" if action == "silent-wait" else "self-maintenance-only"
        else:
            scores["value"] = 1
            scores["efficiency"] = 1
            category = "capability-value"
    else:
        scores["artifact"] = 1 if execution.get("status") == "ok" else 0
        scores["continuity"] = 1
        scores["value"] = 1
        scores["efficiency"] = 1
        scores["agency"] = 1
        category = "capability-value"

    total = sum(scores.values())
    return category, scores, total


def mode_and_cadence(total: int, quiet_hours_active: bool, pattern: dict, action: str) -> tuple[str, str, str]:
    repetitive = pattern.get("repetitive")
    if quiet_hours_active and repetitive:
        return "quiet-hours", "60m", "已进入 quiet hours，且 resident 最近出现重复巡检模式；当前更应该降噪、静默等待，而不是继续机械巡检"
    if quiet_hours_active:
        return "quiet-hours", "45m", "已进入 quiet hours；保持安静、低频、可恢复的 resident 监测更稳"
    if repetitive:
        return "monitoring", "45m", "resident 最近出现重复巡检倾向；暂时保持 monitoring 并降低节奏，等待更明确的新价值信号"
    if total >= 8:
        return "focused", "30m", "resident 最近结果有真实能力价值，可以继续保持 focused 建设态"
    return "monitoring", "30m", "resident 目前以低功耗监测更合适，等待更明确的高价值推进点"


def recent_similar_confirmation(existing_opportunity: dict, primary: dict, cooldown_minutes: float) -> dict | None:
    if not isinstance(existing_opportunity, dict) or not primary:
        return None
    last_confirmed = existing_opportunity.get("lastConfirmedByDeliberation", {}) if isinstance(existing_opportunity.get("lastConfirmedByDeliberation"), dict) else {}
    last_primary = last_confirmed.get("primarySignal", {}) if isinstance(last_confirmed.get("primarySignal"), dict) else {}
    if not last_primary or not same_signal_family(last_primary, primary):
        return None

    elapsed = minutes_since(last_confirmed.get("timestamp"))
    if elapsed is None or elapsed >= cooldown_minutes:
        return None

    return {
        "active": True,
        "elapsedMinutes": round(elapsed, 3),
        "cooldownMinutes": cooldown_minutes,
        "episodeId": last_confirmed.get("episodeId"),
        "outcome": last_confirmed.get("outcome"),
    }


def evaluate_lee_opportunity(latest: dict, category: str, total: int, pattern: dict, deliberation_state: dict, self_direction: dict, existing_opportunity: dict, quiet_hours_active: bool, semantic_assessment: dict) -> dict:
    review = latest.get("review", {}) if isinstance(latest.get("review"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else {}
    semantic = latest.get("semanticWriteback", {}) if isinstance(latest.get("semanticWriteback"), dict) else {}
    verification = latest.get("verification", {}) if isinstance(latest.get("verification"), dict) else {}
    verification_parsed = verification.get("parsed", {}) if isinstance(verification.get("parsed"), dict) else {}
    opportunity_policy = deliberation_state.get("opportunityPolicy", {}) if isinstance(deliberation_state.get("opportunityPolicy"), dict) else {}

    min_surface_score = float(opportunity_policy.get("minSurfaceScore", 4.0) or 4.0)
    min_handoff_score = float(opportunity_policy.get("minPersonaHandoffScore", 6.0) or 6.0)
    confirmed_cooldown_minutes = float(opportunity_policy.get("sameFamilyConfirmationCooldownMinutes", 45) or 45)
    require_semantic_for_surface = bool(opportunity_policy.get("requireSemanticWriteForSurface", True))
    require_external_for_surface = bool(opportunity_policy.get("requireExternalSignalForSurface", True))
    require_high_salience_for_perception_handoff = bool(opportunity_policy.get("requireHighSalienceForPerceptionHandoff", True))
    require_high_salience_or_artifact_diff_for_workspace_handoff = bool(opportunity_policy.get("requireHighSalienceOrArtifactDiffForWorkspaceHandoff", True))
    disallow_self_sensed_persona_handoff_by_default = bool(opportunity_policy.get("disallowSelfSensedPersonaHandoffByDefault", True))

    verification_ok = verification.get("status") == "ok" or verification_parsed.get("status") == "ok"
    semantic_applied = bool(semantic.get("applied"))
    external_signal = signal_is_external(primary)
    salience = primary.get("salience")
    capability_domain = latest.get("capabilityDomain")
    current_track_id = self_direction.get("currentTrackId")
    track_aligned = current_track_id in {"unified-control-plane", "lee-facing-opportunity-routing", "deliberation-threshold-calibration"}
    recent_confirmation = recent_similar_confirmation(existing_opportunity, primary, confirmed_cooldown_minutes)
    semantic_surface_bias = float(semantic_assessment.get("surfaceBias", 0.0) or 0.0)
    semantic_handoff_bias = float(semantic_assessment.get("handoffBias", 0.0) or 0.0)
    semantic_attention = semantic_assessment.get("recommendedAttention")
    artifact_diff_available = bool(semantic_assessment.get("artifactDiffAvailable"))

    evidence_score = 0.0
    evidence = list(semantic_assessment.get("support", []) or [])
    suppressors = list(semantic_assessment.get("suppressors", []) or [])

    if category == "capability-value":
        evidence_score += 1.0
        evidence.append("capability-value")
    if total >= 8:
        evidence_score += 1.0
        evidence.append("high-total-score")
    if semantic_applied:
        evidence_score += 2.0
        evidence.append("semantic-writeback-applied")
    if verification_ok:
        evidence_score += 1.0
        evidence.append("verification-ok")
    if external_signal:
        evidence_score += 1.0
        evidence.append("external-signal")
    if salience == "high":
        evidence_score += 2.0
        evidence.append("high-salience")
    elif salience == "medium":
        evidence_score += 1.0
        evidence.append("medium-salience")
    if capability_domain and capability_domain != "perception":
        evidence_score += 1.0
        evidence.append("beyond-perception-domain")
    if track_aligned:
        evidence_score += 0.5
        evidence.append("track-aligned")
    if semantic_surface_bias:
        evidence_score += semantic_surface_bias
        evidence.append(f"semantic-surface-bias:{round(semantic_surface_bias, 3)}")

    if pattern.get("repetitive"):
        evidence_score -= 2.0
        if "repetitive-loop" not in suppressors:
            suppressors.append("repetitive-loop")
    if quiet_hours_active:
        evidence_score -= 0.5
        if "quiet-hours" not in suppressors:
            suppressors.append("quiet-hours")
    if recent_confirmation:
        evidence_score -= 2.0
        if "same-family-recently-confirmed" not in suppressors:
            suppressors.append("same-family-recently-confirmed")
    if capability_domain == "perception" and primary.get("type") == "screen-changed" and salience != "high":
        evidence_score -= 1.5
        if "ordinary-screen-change-not-strong-enough" not in suppressors:
            suppressors.append("ordinary-screen-change-not-strong-enough")

    missing_evidence = list(semantic_assessment.get("missingEvidence", []) or [])
    must_requirements = []
    if require_semantic_for_surface and not semantic_applied:
        if "missing-semantic-writeback" not in must_requirements:
            must_requirements.append("missing-semantic-writeback")
    if require_external_for_surface and not external_signal:
        if "not-an-external-signal" not in must_requirements:
            must_requirements.append("not-an-external-signal")

    should_surface = evidence_score >= min_surface_score and not must_requirements
    should_handoff = should_surface and (evidence_score + semantic_handoff_bias) >= min_handoff_score and not recent_confirmation
    if require_high_salience_for_perception_handoff and capability_domain == "perception" and primary.get("type") == "screen-changed" and salience != "high":
        should_handoff = False
        if "perception-handoff-requires-high-salience" not in suppressors:
            suppressors.append("perception-handoff-requires-high-salience")
    if require_high_salience_or_artifact_diff_for_workspace_handoff and primary.get("type") == "workspace-changed" and primary.get("provenance") == "user-change" and salience != "high" and not artifact_diff_available:
        should_handoff = False
        if "workspace-handoff-requires-high-salience-or-artifact-diff" not in suppressors:
            suppressors.append("workspace-handoff-requires-high-salience-or-artifact-diff")
    if disallow_self_sensed_persona_handoff_by_default and primary.get("provenance") == "self-sensed":
        should_handoff = False
        if "self-sensed-signal-does-not-deserve-persona-handoff-by-default" not in suppressors:
            suppressors.append("self-sensed-signal-does-not-deserve-persona-handoff-by-default")
    if semantic_attention != "handoff":
        should_handoff = False if should_handoff and semantic_handoff_bias < 1.0 else should_handoff

    reason = "stay-quiet"
    if should_handoff:
        reason = "high-confidence-opportunity-deserves-persona-handoff"
    elif should_surface:
        reason = "candidate-opportunity-worth-keeping-ready"
    elif primary:
        reason = "signal-observed-but-not-yet-worth-interrupting"

    return {
        "shouldSurface": should_surface,
        "shouldHandoff": should_handoff,
        "reason": reason,
        "evidenceScore": round(max(0.0, evidence_score), 3),
        "semanticHandoffScore": round(max(0.0, evidence_score + semantic_handoff_bias), 3),
        "surfaceThreshold": min_surface_score,
        "handoffThreshold": min_handoff_score,
        "evidence": evidence,
        "suppressors": suppressors,
        "missingEvidence": missing_evidence,
        "mustRequirements": must_requirements,
        "trackAligned": track_aligned,
        "recentSimilarConfirmation": recent_confirmation,
        "semanticAssessment": semantic_assessment,
        "primarySignal": primary or None,
        "summary": semantic_assessment.get("meaningSummary") or review.get("summary"),
    }


def recommend_deliberation(latest: dict, pattern: dict, category: str, total: int, current_track_id: str | None, procedural_memory: dict, deliberation_state: dict, semantic_assessment: dict) -> dict:
    review = latest.get("review", {}) if isinstance(latest.get("review"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else {}
    action = latest.get("selectedAction")
    compiled_pattern = matching_deliberation_pattern(procedural_memory, latest, total)
    episode_policy = deliberation_state.get("episodePolicy", {}) if isinstance(deliberation_state.get("episodePolicy"), dict) else {}
    min_total_score = int(episode_policy.get("minTotalScore", 8) or 8)
    cooldown = deliberation_cooldown(deliberation_state, primary, compiled_pattern)
    semantic_attention = semantic_assessment.get("recommendedAttention")
    semantic_surface_bias = float(semantic_assessment.get("surfaceBias", 0.0) or 0.0)
    artifact_diff_available = bool(semantic_assessment.get("artifactDiffAvailable"))
    artifact_preview_available = bool(semantic_assessment.get("artifactPreviewAvailable"))

    recommended = False
    reason = "stay-cheap"

    if (
        action == "inspect-local-signal"
        and primary
        and primary.get("type") == "workspace-changed"
        and primary.get("provenance") == "user-change"
        and category == "capability-value"
        and total >= max(7, min_total_score - 1)
        and (artifact_diff_available or artifact_preview_available or semantic_attention in {"investigate", "handoff"})
    ):
        recommended = True
        reason = "text-artifact-value-deserves-S2-triage"
    elif (
        action == "inspect-local-signal"
        and primary
        and primary.get("provenance") not in {None, "self-write", "self-sensed"}
        and not pattern.get("repetitive")
        and category == "capability-value"
        and total >= min_total_score
    ):
        recommended = True
        reason = "verified-external-signal-may-deserve-S2-triage"
    elif (
        action == "inspect-local-signal"
        and primary
        and semantic_attention in {"investigate", "handoff"}
        and category == "capability-value"
        and total >= max(6, min_total_score - 1)
        and semantic_surface_bias >= 1.0
    ):
        recommended = True
        reason = "semantic-opportunity-may-deserve-S2-triage"
    elif current_track_id == "deliberation-threshold-calibration" and primary:
        recommended = True
        reason = "current-track-is-deliberation-threshold-calibration"
    elif compiled_pattern and category == "capability-value":
        recommended = True
        reason = str(compiled_pattern.get("reason") or "compiled-deliberation-pattern")

    if recommended and cooldown:
        recommended = False
        reason = "same-signal-cooldown-active"

    return {
        "recommended": recommended,
        "reason": reason,
        "primarySignal": primary or None,
        "targetLayer": "S2-deliberation" if recommended else "S1-procedural",
        "compiledPatternId": compiled_pattern.get("id") if compiled_pattern else None,
        "cooldown": cooldown,
    }


def build_reach_out_gate(upgrade: dict, opportunity: dict, semantic_assessment: dict, value_signal: dict, quiet_hours_active: bool) -> dict:
    info = upgrade.get("informationScout", {}) if isinstance(upgrade.get("informationScout"), dict) else {}
    drive = info.get("homeostaticDrive", {}) if isinstance(info.get("homeostaticDrive"), dict) else {}
    help_evidence = load_optional_json(LEE_SERVICE_HELP_EVIDENCE_PATH)
    help_verification = help_evidence.get("verification", {}) if isinstance(help_evidence.get("verification"), dict) else {}
    help_recommendation = help_evidence.get("recommendation", {}) if isinstance(help_evidence.get("recommendation"), dict) else {}
    help_packet_ok = help_verification.get("status") == "ok" and bool(help_evidence.get("usefulActions"))

    lee_service = float(drive.get("leeServiceDrive", 0.0) or 0.0)
    interruption_cost = float(drive.get("interruptionCost", 1.0) or 1.0)
    recommended_mode = drive.get("recommendedMode")
    has_semantic_value = bool(value_signal.get("detected") or opportunity.get("shouldSurface") or help_packet_ok)
    must_requirements = list(opportunity.get("mustRequirements", []) or [])
    missing = list(opportunity.get("missingEvidence", []) or [])

    # A verified help packet satisfies the "semantic value" evidence needed to
    # prepare useful help, but it does not by itself override the external-signal
    # or interruption gates for visible contact. This separates preparation from
    # messaging, preventing leeServiceDrive from becoming noisy.
    if help_packet_ok and "missing-semantic-help-evidence" in missing:
        missing = [x for x in missing if x != "missing-semantic-help-evidence"]

    surface_allowed = bool(
        has_semantic_value
        and not missing
        and not must_requirements
        and interruption_cost < 0.7
        and not quiet_hours_active
        and semantic_assessment.get("recommendedAttention") in {"investigate", "handoff"}
        and bool(help_recommendation.get("shouldSurfaceToLee") or opportunity.get("shouldSurface"))
    )
    should_surface = bool(surface_allowed and lee_service >= 0.72)
    should_prepare = bool(lee_service >= 0.62 and not should_surface)
    decision = "surface-brief-helpful-contact" if should_surface else ("prepare-help-silently-with-evidence" if should_prepare and help_packet_ok else ("prepare-help-silently" if should_prepare else "hold"))
    reason = "value-and-interruption-gates-pass" if should_surface else ("help-evidence-consumed-contact-gate-still-closed" if help_packet_ok and should_prepare else "service-drive-present-but-opportunity-gates-not-met")
    return {
        "enabled": True,
        "leeServiceDrive": round(lee_service, 3),
        "interruptionCost": round(interruption_cost, 3),
        "driveRecommendedMode": recommended_mode,
        "shouldPrepare": should_prepare,
        "shouldSurface": should_surface,
        "decision": decision,
        "reason": reason,
        "requirements": [
            "semantic value signal or opportunity.shouldSurface or verified helpEvidence packet",
            "no mustRequirements",
            "interruptionCost < 0.7",
            "not quiet-hours",
            "semanticAttention investigate/handoff",
            "helpEvidence recommendation allows surface before visible contact",
        ],
        "missingEvidence": missing,
        "mustRequirements": must_requirements,
        "helpEvidence": {
            "consumed": bool(help_packet_ok),
            "status": help_verification.get("status"),
            "evidenceScore": help_verification.get("evidenceScore"),
            "usefulActionCount": len(help_evidence.get("usefulActions", []) or []),
            "recommendationMode": help_recommendation.get("mode"),
            "shouldSurfaceToLee": bool(help_recommendation.get("shouldSurfaceToLee")),
            "timestamp": help_evidence.get("timestamp"),
        },
        "principle": "leeServiceDrive may prepare helpful contact when evidence is verified, but visible reach-out still requires value, interruption, and explicit surface gates",
    }


def build_value_signal(primary: dict, semantic_assessment: dict, opportunity: dict, deliberation_recommendation: dict) -> dict:
    semantic_attention = semantic_assessment.get("recommendedAttention")
    artifact_diff_available = bool(semantic_assessment.get("artifactDiffAvailable"))
    artifact_preview_available = bool(semantic_assessment.get("artifactPreviewAvailable"))
    signal_type = primary.get("type") if isinstance(primary, dict) else None
    provenance = primary.get("provenance") if isinstance(primary, dict) else None

    detected = False
    kind = None
    reason = "no-meaningful-value-signal"
    suggested_next_layer = deliberation_recommendation.get("targetLayer", "S1-procedural")
    summary = semantic_assessment.get("meaningSummary")

    if (
        signal_type == "workspace-changed"
        and provenance == "user-change"
        and (artifact_diff_available or artifact_preview_available or semantic_attention in {"investigate", "handoff"})
    ):
        detected = True
        kind = "text-artifact-value"
        reason = "workspace-user-change-has-text-value"
    elif opportunity.get("shouldSurface") or deliberation_recommendation.get("recommended"):
        detected = True
        kind = "candidate-opportunity-value"
        reason = "surface-or-deliberation-value-detected"

    return {
        "detected": detected,
        "kind": kind,
        "reason": reason,
        "suggestedNextLayer": suggested_next_layer,
        "summary": summary,
        "semanticAttention": semantic_attention,
        "artifactDiffAvailable": artifact_diff_available,
        "artifactPreviewAvailable": artifact_preview_available,
        "primarySignal": primary or None,
    }


def main() -> None:
    action_state = load_optional_json(ACTION_STATE_PATH)
    self_state = load_optional_json(SELF_STATE_PATH)
    session_mode = load_optional_json(SESSION_MODE_PATH)
    homeostasis = load_optional_json(HOMEOSTASIS_PATH)
    continuity = load_optional_json(CONTINUITY_PATH)
    self_direction = load_optional_json(SELF_DIRECTION_PATH)
    deliberation = load_optional_json(DELIBERATION_PATH)
    attention = load_optional_json(ATTENTION_PATH)
    resident_config = load_optional_json(RESIDENT_CONFIG_PATH)
    capability_registry = load_capability_registry()
    procedural_memory = load_optional_json(PROCEDURAL_PATH)
    screen_state = load_optional_json(SCREEN_STATE_PATH)
    upgrade = load_optional_json(UPGRADE_PATH)

    recent_executions = list(action_state.get("recentExecutions", []) or [])
    selected = [item for item in recent_executions if item.get("selectedAction")]
    latest = selected[-1] if selected else None
    if latest is None:
        result = {"applied": False, "reason": "no-selected-resident-execution", "timestamp": now_iso()}
        save_json(ROOT / resident_config.get("reflectionStatePath", str(DEFAULT_REFLECTION_PATH.relative_to(ROOT)).replace("\\", "/")), result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    current = now()
    quiet_hours_active = in_quiet_hours(homeostasis, current)
    pattern = recent_loop_pattern(action_state)
    category, scores, total = classify_value(latest, pattern)
    mode, cadence, mode_reason = mode_and_cadence(total, quiet_hours_active, pattern, latest.get("selectedAction"))
    opportunity_path_value = resident_config.get("opportunityReviewPath", str(DEFAULT_OPPORTUNITY_PATH.relative_to(ROOT)).replace("\\", "/"))
    existing_opportunity = load_optional_json(ROOT / opportunity_path_value)
    semantic_assessment = assess_opportunity_semantics(
        latest=latest,
        pattern=pattern,
        category=category,
        total=total,
        quiet_hours_active=quiet_hours_active,
        self_state=self_state,
        self_direction=self_direction,
        continuity=continuity,
        deliberation_state=deliberation,
        existing_opportunity=existing_opportunity,
        screen_state=screen_state,
    )
    opportunity = evaluate_lee_opportunity(latest, category, total, pattern, deliberation, self_direction, existing_opportunity, quiet_hours_active, semantic_assessment)
    deliberation_recommendation = recommend_deliberation(latest, pattern, category, total, self_direction.get("currentTrackId"), procedural_memory, deliberation, semantic_assessment)
    value_signal = build_value_signal(latest.get("review", {}).get("primarySignal", {}) if isinstance(latest.get("review"), dict) else {}, semantic_assessment, opportunity, deliberation_recommendation)
    reach_out_gate = build_reach_out_gate(upgrade, opportunity, semantic_assessment, value_signal, quiet_hours_active)
    opportunity["reachOutGate"] = reach_out_gate

    threshold = int(homeostasis.get("lowActivityRule", {}).get("quietStreakThreshold", 3))
    quiet_streak = int(continuity.get("quietStreak", 0))
    if total <= 4:
        quiet_streak += 1
    elif total >= 8:
        quiet_streak = 0
    else:
        quiet_streak = max(0, quiet_streak - 1)

    low_activity = quiet_streak >= threshold or quiet_hours_active or pattern.get("repetitive")

    continuity["quietStreak"] = quiet_streak
    continuity["lowActivityWindow"] = low_activity
    continuity["recommendedCadence"] = cadence
    continuity["modeReason"] = mode_reason
    continuity["updatedAt"] = now_iso()

    session_mode["mode"] = mode
    session_mode["interruptibility"] = "low" if mode in {"quiet-hours", "waiting"} else ("medium" if mode == "monitoring" else "normal")
    session_mode["modeReason"] = mode_reason
    session_mode["updatedAt"] = now_iso()

    self_state["currentMode"] = mode
    self_state["updatedAt"] = now_iso()

    self_direction["lastReflectionCategory"] = category
    self_direction["lastReflectionScore"] = total
    self_direction["trackHealth"] = "healthy" if total >= 7 and not pattern.get("repetitive") else ("stale" if pattern.get("repetitive") else "mixed")
    self_direction["lastOpportunityDecision"] = opportunity
    self_direction["lastSemanticAssessment"] = {
        "semanticClass": semantic_assessment.get("semanticClass"),
        "recommendedAttention": semantic_assessment.get("recommendedAttention"),
        "meaningSummary": semantic_assessment.get("meaningSummary"),
        "surfaceBias": semantic_assessment.get("surfaceBias"),
        "handoffBias": semantic_assessment.get("handoffBias"),
        "timestamp": semantic_assessment.get("timestamp"),
    }
    self_direction["lastValueSignal"] = value_signal
    self_direction["lastCapabilityId"] = latest.get("capabilityId")
    self_direction["lastCapabilityDomain"] = latest.get("capabilityDomain")
    self_direction["updatedAt"] = now_iso()

    deliberation["currentLayer"] = deliberation_recommendation.get("targetLayer", deliberation.get("currentLayer", "S1-procedural"))
    deliberation["lastRecommendation"] = {
        **deliberation_recommendation,
        "timestamp": now_iso(),
    }
    deliberation["updatedAt"] = now_iso()

    attention["currentAttentionTarget"] = self_state.get("activeGoal") or self_state.get("currentFocus") or attention.get("currentAttentionTarget")
    attention["activeCapabilityIds"] = list(self_state.get("activeCapabilityIds", []) or [])
    attention["updatedAt"] = now_iso()

    save_json(CONTINUITY_PATH, continuity)
    save_json(SESSION_MODE_PATH, session_mode)
    save_json(SELF_STATE_PATH, self_state)
    save_json(SELF_DIRECTION_PATH, self_direction)
    save_json(DELIBERATION_PATH, deliberation)
    save_json(ATTENTION_PATH, attention)

    reflection = {
        "applied": True,
        "timestamp": now_iso(),
        "latestAction": latest.get("selectedAction"),
        "latestCapabilityId": latest.get("capabilityId"),
        "latestCapabilityDomain": latest.get("capabilityDomain"),
        "valueCategory": category,
        "scores": scores,
        "totalScore": total,
        "pattern": pattern,
        "quietHoursActive": quiet_hours_active,
        "mode": mode,
        "modeReason": mode_reason,
        "recommendedCadence": cadence,
        "quietStreak": quiet_streak,
        "lowActivityWindow": low_activity,
        "currentTrackId": self_direction.get("currentTrackId"),
        "activeCapabilityIds": list(self_state.get("activeCapabilityIds", []) or []),
        "trackHealth": self_direction.get("trackHealth"),
        "registryBacked": bool(capability_registry.get("policy", {}).get("registryIsSourceOfTruth")),
        "semanticAssessment": semantic_assessment,
        "valueSignal": value_signal,
        "opportunity": opportunity,
        "reachOutGate": reach_out_gate,
        "deliberationRecommendation": deliberation_recommendation,
    }
    reflection_path_value = resident_config.get("reflectionStatePath", str(DEFAULT_REFLECTION_PATH.relative_to(ROOT)).replace("\\", "/"))
    save_json(ROOT / reflection_path_value, reflection)
    opportunity_payload = {
        "timestamp": now_iso(),
        "currentTrackId": self_direction.get("currentTrackId"),
        "semanticAssessment": semantic_assessment,
        "valueSignal": value_signal,
        "decision": opportunity,
        "reachOutGate": reach_out_gate,
        "deliberationRecommendation": deliberation_recommendation,
        "mode": mode,
        "totalScore": total,
    }
    if isinstance(existing_opportunity, dict) and existing_opportunity.get("lastConfirmedByDeliberation"):
        opportunity_payload["lastConfirmedByDeliberation"] = existing_opportunity.get("lastConfirmedByDeliberation")
    save_json(ROOT / opportunity_path_value, opportunity_payload)
    print(json.dumps(reflection, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
