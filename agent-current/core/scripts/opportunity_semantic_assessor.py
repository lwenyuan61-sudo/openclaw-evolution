from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
ACTION_STATE_PATH = CORE / "action-state.json"
SELF_STATE_PATH = CORE / "self-state.json"
SELF_DIRECTION_PATH = AUTO / "self-direction-state.json"
CONTINUITY_PATH = AUTO / "continuity-state.json"
DELIBERATION_PATH = CORE / "deliberation-state.json"
OPPORTUNITY_PATH = STATE / "lee_opportunity_review.json"
SCREEN_STATE_PATH = STATE / "screen_state.json"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


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
        # Artifact signals are not one generic family: path + old/new content hashes are
        # the identity evidence that prevents unrelated text changes from being deduped.
        return workspace_signal_identity(a) == workspace_signal_identity(b)
    return True


def signal_is_external(primary: dict) -> bool:
    if not isinstance(primary, dict):
        return False
    return primary.get("provenance") not in {None, "self-write", "self-sensed"}


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


def relation_to_focus(action: str | None, capability_domain: str | None, self_state: dict, self_direction: dict, primary: dict | None) -> str:
    current_track_id = self_direction.get("currentTrackId")
    if action == "continue-focus" and not primary:
        return "core-focus"
    if capability_domain in {"continuity", "deliberation"}:
        return "core-focus"
    if primary and primary.get("type") == "workspace-changed" and current_track_id == "unified-control-plane":
        return "adjacent-artifact"
    if capability_domain == "perception" and primary and current_track_id == "unified-control-plane":
        return "adjacent-sensing"
    if self_state.get("activeGoal") or self_state.get("currentFocus"):
        return "adjacent"
    return "background"


def semantic_class_for(action: str | None, primary: dict, semantic_applied: bool, verification_ok: bool, recent_confirmation: dict | None, artifact_diff_available: bool) -> str:
    signal_type = primary.get("type") if isinstance(primary, dict) else None
    salience = primary.get("salience") if isinstance(primary, dict) else None
    provenance = primary.get("provenance") if isinstance(primary, dict) else None

    if action == "silent-wait":
        return "quiet-monitoring"
    if action == "continue-focus" and not primary:
        return "focus-maintenance"
    if signal_type == "screen-changed":
        if recent_confirmation:
            return "already-confirmed-screen-shift"
        if salience == "high":
            return "attention-worthy-screen-shift"
        if semantic_applied and verification_ok:
            return "candidate-interaction-shift"
        return "ambient-screen-shift"
    if signal_type == "workspace-changed":
        if provenance == "self-write":
            return "self-generated-artifact-churn"
        if recent_confirmation:
            return "already-confirmed-user-artifact-shift"
        if (salience == "high" or artifact_diff_available) and verification_ok:
            return "attention-worthy-user-artifact-shift"
        if semantic_applied and verification_ok:
            return "candidate-user-artifact-shift"
        if verification_ok:
            return "user-artifact-shift-needs-more-context"
        return "unverified-user-artifact-shift"
    if signal_type == "device-snapshot-present":
        if semantic_applied and verification_ok:
            return "device-state-refresh"
        return "ambient-device-refresh"
    if primary and signal_is_external(primary):
        if semantic_applied:
            return "candidate-external-opportunity"
        return "external-change-needs-more-context"
    if semantic_applied:
        return "durable-capability-progress"
    return "internal-maintenance"


def meaning_summary(semantic_class: str, primary: dict, relation: str, recent_confirmation: dict | None) -> str:
    signal_type = primary.get("type") if isinstance(primary, dict) else None
    provenance = primary.get("provenance") if isinstance(primary, dict) else None
    path = primary.get("path") if isinstance(primary, dict) else None
    if semantic_class == "focus-maintenance":
        return "这更像当前主线的连续维护，而不是新的外部机会。"
    if semantic_class == "quiet-monitoring":
        return "这更像一次主动压噪后的静默监测，不值得升级。"
    if semantic_class == "ambient-device-refresh":
        return "这更像一次设备快照刷新或本机感知回响，默认应留在低噪声内部循环。"
    if semantic_class == "device-state-refresh":
        return "设备状态发生了可验证刷新，但当前仍更像低成本感知更新，而不是值得打扰 Lee 的机会。"
    if semantic_class == "ambient-screen-shift":
        return f"这次 {provenance or 'external'} {signal_type or 'signal'} 更像普通环境变化，值得记录但暂不值得本人格接手。"
    if semantic_class == "already-confirmed-screen-shift":
        return "这次变化和最近已确认过的同类机会属于同一家族，当前更适合保留为候选而不是再次唤醒本人格。"
    if semantic_class == "attention-worthy-screen-shift":
        return "这次屏幕变化更像真正值得进一步调查的交互转折点，应该优先做受限深推理。"
    if semantic_class == "candidate-interaction-shift":
        return "这次变化已经不只是 hash 变化，而更像一次候选交互转折；先调查，再决定是否上浮。"
    if semantic_class == "self-generated-artifact-churn":
        return f"这次 workspace 变化更像系统自己的写回痕迹（{path or provenance or 'internal artifact'}），默认不应误判成 Lee-facing 机会。"
    if semantic_class == "already-confirmed-user-artifact-shift":
        return f"这次用户侧 artifact 变化（{path or 'workspace change'}）与最近已确认过的同类变化过近，当前更适合保留候选而不是再次上浮。"
    if semantic_class == "attention-worthy-user-artifact-shift":
        return f"这次用户侧 artifact 变化（{path or 'workspace change'}）已经足够强，值得优先进入受限调查。"
    if semantic_class == "candidate-user-artifact-shift":
        return f"这次用户侧 artifact 变化（{path or 'workspace change'}）已具备候选机会价值，应先调查内容含义，再决定是否继续上浮。"
    if semantic_class == "user-artifact-shift-needs-more-context":
        return f"这次用户侧 artifact 变化（{path or 'workspace change'}）已被验证存在，但仍缺少内容层证据，先保留候选更稳。"
    if semantic_class == "unverified-user-artifact-shift":
        return f"检测到用户侧 artifact 变化（{path or 'workspace change'}），但当前验证仍偏弱，不宜直接上浮。"
    if semantic_class == "candidate-external-opportunity":
        return "这次外部变化与当前主线有连接，存在上浮价值，但仍应先补证据。"
    if semantic_class == "durable-capability-progress":
        return f"这更像一次与当前主线 {relation} 的真实能力进展，可继续保留为候选价值。"
    return "这更像内部维护或弱证据变化，当前不值得升级。"


def assess_opportunity_semantics(*, latest: dict, pattern: dict, category: str, total: int, quiet_hours_active: bool, self_state: dict, self_direction: dict, continuity: dict, deliberation_state: dict, existing_opportunity: dict, screen_state: dict | None = None) -> dict:
    review = latest.get("review", {}) if isinstance(latest.get("review"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else {}
    verification = latest.get("verification", {}) if isinstance(latest.get("verification"), dict) else {}
    verification_parsed = verification.get("parsed", {}) if isinstance(verification.get("parsed"), dict) else {}
    semantic = latest.get("semanticWriteback", {}) if isinstance(latest.get("semanticWriteback"), dict) else {}

    action = latest.get("selectedAction")
    capability_domain = latest.get("capabilityDomain")
    semantic_applied = bool(semantic.get("applied"))
    verification_ok = verification.get("status") == "ok" or verification_parsed.get("status") == "ok"
    external_signal = signal_is_external(primary)
    salience = primary.get("salience") if primary else None
    screen_hash = screen_state.get("screenHash") if isinstance(screen_state, dict) else None
    image_path = screen_state.get("imagePath") if isinstance(screen_state, dict) else None
    artifact_diff_available = bool(primary.get("artifactDiffAvailable")) or bool(primary.get("oldContentHash") and primary.get("newContentHash") and primary.get("oldContentHash") != primary.get("newContentHash"))
    artifact_preview_available = bool(verification_parsed.get("contentPreviewAvailable"))

    opportunity_policy = deliberation_state.get("opportunityPolicy", {}) if isinstance(deliberation_state.get("opportunityPolicy"), dict) else {}
    same_family_cooldown = float(opportunity_policy.get("sameFamilyConfirmationCooldownMinutes", 45) or 45)
    recent_confirmation = recent_similar_confirmation(existing_opportunity, primary, same_family_cooldown)
    relation = relation_to_focus(action, capability_domain, self_state, self_direction, primary)
    semantic_class = semantic_class_for(action, primary, semantic_applied, verification_ok, recent_confirmation, artifact_diff_available)

    novelty = "low"
    if external_signal and not recent_confirmation:
        novelty = "medium"
    if salience == "high" and external_signal and not recent_confirmation:
        novelty = "high"
    if pattern.get("repetitive"):
        novelty = "low"

    stakes = "low"
    if semantic_applied or (verification_ok and external_signal):
        stakes = "medium"
    if salience == "high" and semantic_applied and external_signal:
        stakes = "high"

    urgency = "low"
    if stakes == "medium" and external_signal:
        urgency = "medium"
    if stakes == "high" and not recent_confirmation:
        urgency = "high"

    user_value_likelihood = "low"
    if external_signal or semantic_applied:
        user_value_likelihood = "medium"
    if stakes == "high" and relation in {"core-focus", "adjacent-sensing", "adjacent-artifact", "adjacent"}:
        user_value_likelihood = "high"

    support = []
    suppressors = []
    missing_evidence = []
    surface_bias = 0.0
    handoff_bias = -1.0

    if category == "capability-value":
        support.append("capability-value")
        surface_bias += 0.5
    if total >= 8:
        support.append("high-total-score")
        surface_bias += 0.5
    if semantic_applied:
        support.append("semantic-writeback-applied")
        surface_bias += 1.0
    if verification_ok:
        support.append("verification-ok")
        surface_bias += 0.5
    if external_signal:
        support.append("external-signal")
        surface_bias += 0.5
    if relation == "core-focus":
        support.append("core-focus-aligned")
        surface_bias += 0.25
    elif relation == "adjacent-artifact":
        support.append("adjacent-artifact-to-current-focus")
        surface_bias += 0.35
    elif relation == "adjacent-sensing":
        support.append("adjacent-sensing-to-current-focus")
        surface_bias += 0.2
    if image_path and primary and primary.get("newHash") == screen_hash:
        support.append("visual-evidence-available")
        surface_bias += 0.2
    if artifact_diff_available:
        support.append("artifact-diff-available")
        surface_bias += 0.6
        handoff_bias += 2.2
    elif artifact_preview_available:
        support.append("artifact-preview-available")
        surface_bias += 0.3
        handoff_bias += 0.4

    if semantic_class in {"focus-maintenance", "quiet-monitoring", "internal-maintenance"}:
        handoff_bias -= 1.0
    elif semantic_class == "ambient-screen-shift":
        support.append("ambient-shift")
        handoff_bias -= 1.0
    elif semantic_class == "already-confirmed-screen-shift":
        support.append("similar-opportunity-already-confirmed")
        surface_bias += 0.3
        handoff_bias -= 1.5
    elif semantic_class == "candidate-interaction-shift":
        support.append("candidate-interaction-shift")
        surface_bias += 0.8
        handoff_bias += 0.4
    elif semantic_class == "attention-worthy-screen-shift":
        support.append("attention-worthy-screen-shift")
        surface_bias += 1.2
        handoff_bias += 1.0
    elif semantic_class == "self-generated-artifact-churn":
        support.append("self-generated-artifact-churn")
        handoff_bias -= 1.6
    elif semantic_class == "unverified-user-artifact-shift":
        support.append("unverified-user-artifact-shift")
        surface_bias += 0.4
        handoff_bias -= 2.6
    elif semantic_class == "user-artifact-shift-needs-more-context":
        support.append("verified-user-artifact-shift")
        surface_bias += 0.9
        handoff_bias -= 3.2
    elif semantic_class == "candidate-user-artifact-shift":
        support.append("candidate-user-artifact-shift")
        surface_bias += 1.3
        handoff_bias -= 2.8
    elif semantic_class == "already-confirmed-user-artifact-shift":
        support.append("similar-user-artifact-already-confirmed")
        surface_bias += 0.4
        handoff_bias -= 3.8
    elif semantic_class == "attention-worthy-user-artifact-shift":
        support.append("attention-worthy-user-artifact-shift")
        surface_bias += 1.6
        handoff_bias += 1.2
    elif semantic_class == "ambient-device-refresh":
        support.append("ambient-device-refresh")
        handoff_bias -= 1.4
    elif semantic_class == "device-state-refresh":
        support.append("device-state-refresh")
        surface_bias += 0.2
        handoff_bias -= 1.6
    elif semantic_class == "candidate-external-opportunity":
        support.append("candidate-external-opportunity")
        surface_bias += 1.0
        handoff_bias += 0.6
    elif semantic_class == "durable-capability-progress":
        support.append("durable-capability-progress")
        surface_bias += 0.7
        handoff_bias += 0.2

    if recent_confirmation:
        suppressors.append("same-family-recently-confirmed")
        handoff_bias -= 1.0
    if pattern.get("repetitive"):
        suppressors.append("repetitive-pattern")
        surface_bias -= 0.8
        handoff_bias -= 0.8
    if quiet_hours_active:
        suppressors.append("quiet-hours")
        surface_bias -= 0.3
        handoff_bias -= 0.3
    if capability_domain == "perception" and primary.get("type") == "screen-changed" and salience != "high":
        suppressors.append("ordinary-screen-change-not-strong-enough")
        handoff_bias -= 1.0
        missing_evidence.append("need-screen-content-semantics-or-high-salience")
    if primary.get("type") == "workspace-changed":
        if primary.get("provenance") == "self-write":
            suppressors.append("self-generated-workspace-write")
            surface_bias -= 1.0
            handoff_bias -= 1.0
        if not primary.get("path"):
            missing_evidence.append("need-workspace-path")
        elif primary.get("provenance") == "user-change" and salience != "high" and not artifact_diff_available:
            missing_evidence.append("need-artifact-diff-or-high-salience")
    if primary.get("type") == "device-snapshot-present":
        suppressors.append("device-refresh-low-stakes")
        surface_bias -= 0.6
        handoff_bias -= 1.2
        missing_evidence.append("need-device-delta-with-user-impact")
    if not semantic_applied:
        missing_evidence.append("need-durable-semantic-writeback")
    if primary and not verification_ok:
        missing_evidence.append("need-verification")
    if primary and not external_signal:
        missing_evidence.append("need-external-signal")
    if salience != "high" and handoff_bias >= 0:
        missing_evidence.append("need-higher-stakes-before-persona-handoff")

    recommended_attention = "hold"
    if surface_bias >= 1.5:
        recommended_attention = "investigate"
    if handoff_bias >= 1.5 and urgency in {"medium", "high"}:
        recommended_attention = "handoff"
    elif surface_bias >= 0.5 and recommended_attention == "hold":
        recommended_attention = "watch"

    # Unified-control-plane routing: compile the repeated wake observations into
    # an explicit low-cost layer recommendation. This keeps ordinary resident
    # pulses in S0/S1, routes investigable but local evidence into bounded S2,
    # and reserves persona handoff for verified high-value cases.
    layer = "S1-procedural"
    layer_reasons: list[str] = []
    if semantic_class in {"focus-maintenance", "quiet-monitoring", "internal-maintenance"}:
        layer = "S1-procedural"
        layer_reasons.append("cheap-focus-or-monitoring")
    elif semantic_class in {"ambient-screen-shift", "ambient-device-refresh", "device-state-refresh"}:
        layer = "S1-procedural"
        layer_reasons.append("ambient-or-low-stakes-signal")
    elif recent_confirmation or pattern.get("repetitive"):
        layer = "S1-procedural"
        layer_reasons.append("same-family-or-repetitive-cooldown")
    elif recommended_attention == "handoff":
        layer = "S2-persona-handoff-candidate"
        layer_reasons.append("verified-high-value-handoff-threshold")
    elif recommended_attention == "investigate":
        layer = "S2-limited-investigation"
        layer_reasons.append("surface-threshold-met-needs-evidence")
    elif recommended_attention == "watch":
        layer = "S1-watch"
        layer_reasons.append("watch-threshold-without-handoff-evidence")
    if "need-verification" in missing_evidence or "need-durable-semantic-writeback" in missing_evidence:
        if layer.startswith("S2") and recommended_attention != "handoff":
            layer_reasons.append("keep-s2-bounded-until-verification")
        elif not layer.startswith("S2"):
            layer_reasons.append("missing-evidence-keeps-in-s1")
    layer_gate = {
        "recommendedLayer": layer,
        "reasons": layer_reasons or ["default-stay-cheap"],
        "s1WhenAny": [
            "focus-maintenance",
            "quiet-monitoring",
            "ambient-screen-shift",
            "ambient-device-refresh",
            "same-family-recently-confirmed",
            "repetitive-pattern",
        ],
        "s2WhenAny": [
            "attention-worthy-user-artifact-shift",
            "attention-worthy-screen-shift",
            "candidate-external-opportunity-with-verification",
            "verified-high-value-handoff-threshold",
        ],
        "personaHandoffRequires": [
            "recommendedAttention=handoff",
            "verification-ok",
            "semantic evidence",
            "urgency medium/high",
            "no same-family cooldown",
        ],
    }

    return {
        "timestamp": now_iso(),
        "semanticClass": semantic_class,
        "meaningSummary": meaning_summary(semantic_class, primary, relation, recent_confirmation),
        "relationToCurrentFocus": relation,
        "novelty": novelty,
        "stakes": stakes,
        "urgency": urgency,
        "userValueLikelihood": user_value_likelihood,
        "recommendedAttention": recommended_attention,
        "surfaceBias": round(surface_bias, 3),
        "handoffBias": round(handoff_bias, 3),
        "support": support,
        "suppressors": suppressors,
        "missingEvidence": list(dict.fromkeys(missing_evidence)),
        "visualEvidenceAvailable": bool(image_path),
        "screenImagePath": image_path,
        "artifactDiffAvailable": artifact_diff_available,
        "artifactPreviewAvailable": artifact_preview_available,
        "recentSimilarConfirmation": recent_confirmation,
        "layerRouting": layer_gate,
        "primarySignal": primary or None,
    }


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
        1 for item in window
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


def main() -> None:
    action_state = load_optional_json(ACTION_STATE_PATH)
    self_state = load_optional_json(SELF_STATE_PATH)
    self_direction = load_optional_json(SELF_DIRECTION_PATH)
    continuity = load_optional_json(CONTINUITY_PATH)
    deliberation = load_optional_json(DELIBERATION_PATH)
    opportunity = load_optional_json(OPPORTUNITY_PATH)
    screen_state = load_optional_json(SCREEN_STATE_PATH)

    recent_executions = list(action_state.get("recentExecutions", []) or [])
    selected = [item for item in recent_executions if item.get("selectedAction")]
    latest = selected[-1] if selected else None
    if latest is None:
        print(json.dumps({
            "status": "skipped",
            "reason": "no-selected-resident-execution",
            "timestamp": now_iso(),
        }, ensure_ascii=False, indent=2))
        return

    pattern = recent_loop_pattern(action_state)
    category = "capability-value"
    total = 0
    if isinstance(latest.get("review"), dict) and isinstance(latest.get("review", {}).get("scores"), dict):
        total = sum(int(v or 0) for v in latest.get("review", {}).get("scores", {}).values())
    result = assess_opportunity_semantics(
        latest=latest,
        pattern=pattern,
        category=category,
        total=total,
        quiet_hours_active=False,
        self_state=self_state,
        self_direction=self_direction,
        continuity=continuity,
        deliberation_state=deliberation,
        existing_opportunity=opportunity,
        screen_state=screen_state,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
