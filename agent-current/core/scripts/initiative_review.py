from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
CAPABILITY_PATH = CORE / "capability-registry.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def hours_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return (datetime.now(timezone.utc).astimezone() - dt).total_seconds() / 3600.0


def minutes_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return (datetime.now(timezone.utc).astimezone() - dt).total_seconds() / 60.0


def score_candidate(candidate: dict, self_state: dict, continuity: dict) -> float:
    score = 0.0
    score += float(candidate.get("leeValue", 0.0)) * 3.0
    score += float(candidate.get("continuityWeight", 0.0)) * 2.0
    score += float(candidate.get("feasibility", 0.0)) * 2.0
    score += float(candidate.get("learningLeverage", 0.0)) * 1.5
    score -= float(candidate.get("noiseRisk", 0.0)) * 1.5

    if candidate.get("status") == "active":
        score += 0.3
    if candidate.get("status") == "queued":
        score -= 0.1

    if candidate.get("focus") == self_state.get("currentFocus"):
        score += 0.5
    if candidate.get("goal") == self_state.get("activeGoal"):
        score += 0.35

    if continuity.get("lowActivityWindow"):
        score -= float(candidate.get("noiseRisk", 0.0)) * 0.4

    return round(score, 3)


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def related_capability_ids(candidate: dict, capability_registry: dict) -> list[str]:
    declared = list(candidate.get("relatedCapabilities", []) or [])
    valid_ids = {
        item.get("id")
        for item in list(capability_registry.get("abilities", []) or [])
        if isinstance(item, dict) and item.get("id")
    }
    if not valid_ids:
        return [item for item in declared if item]
    return [item for item in declared if item in valid_ids]


def main() -> None:
    timestamp = now_iso()

    self_state_path = CORE / "self-state.json"
    continuity_path = AUTO / "continuity-state.json"
    register_path = AUTO / "goal-register.json"
    direction_state_path = AUTO / "self-direction-state.json"
    attention_state_path = CORE / "attention-state.json"
    deliberation_state_path = CORE / "deliberation-state.json"
    reflection_state_path = STATE / "resident_reflection.json"
    capability_registry = load_optional_json(CAPABILITY_PATH)

    self_state = load_json(self_state_path)
    continuity = load_json(continuity_path)
    register = load_json(register_path)
    direction_state = load_json(direction_state_path)
    attention_state = load_optional_json(attention_state_path)
    deliberation_state = load_optional_json(deliberation_state_path)
    reflection_state = load_optional_json(reflection_state_path)

    policy = register.get("policy", {})
    switch_after_stale_hours = float(policy.get("switchAfterStaleHours", 6))
    min_quiet_streak = int(policy.get("minQuietStreakForReselection", 3))
    prefer_immediate_continuation_after_progress = bool(policy.get("preferImmediateContinuationAfterProgress", True))
    immediate_continuation_window_minutes = float(policy.get("immediateContinuationWindowMinutes", 20) or 20)

    stale_hours = hours_since(self_state.get("lastMeaningfulProgressAt"))
    recent_progress_minutes = minutes_since(self_state.get("lastMeaningfulProgressAt"))
    quiet_streak = int(continuity.get("quietStreak", 0) or 0)
    current_focus = self_state.get("currentFocus")

    candidates = [c for c in list(register.get("candidates", [])) if c.get("status") not in {"blocked", "done", "disabled"}]
    reflection_total = int(reflection_state.get("totalScore", 0) or 0)
    reflection_pattern = reflection_state.get("pattern", {}) if isinstance(reflection_state.get("pattern"), dict) else {}
    repetitive = bool(reflection_pattern.get("repetitive"))
    deliberation_recommendation = deliberation_state.get("lastRecommendation", {}) if isinstance(deliberation_state.get("lastRecommendation"), dict) else {}
    reflection_opportunity = reflection_state.get("opportunity", {}) if isinstance(reflection_state.get("opportunity"), dict) else {}
    surfaced_opportunity_active = bool(reflection_opportunity.get("shouldSurface") or reflection_opportunity.get("shouldHandoff"))
    semantic_assessment = reflection_state.get("semanticAssessment", {}) if isinstance(reflection_state.get("semanticAssessment"), dict) else {}
    layer_routing = semantic_assessment.get("layerRouting", {}) if isinstance(semantic_assessment.get("layerRouting"), dict) else {}
    shared_threshold_context = {
        "timestamp": timestamp,
        "recommendedLayer": layer_routing.get("recommendedLayer"),
        "layerRoutingReasons": layer_routing.get("reasons", []),
        "semanticAttention": semantic_assessment.get("recommendedAttention"),
        "semanticClass": semantic_assessment.get("semanticClass"),
        "cooldown": semantic_assessment.get("recentSimilarConfirmation") or deliberation_recommendation.get("cooldown"),
        "deliberationRecommended": bool(deliberation_recommendation.get("recommended")),
        "deliberationReason": deliberation_recommendation.get("reason"),
        "principle": "initiative/reflection/ranker share the same S1/S2 threshold and same-family cooldown context",
    }

    scored = []
    for candidate in candidates:
        score = score_candidate(candidate, self_state, continuity)
        capability_ids = related_capability_ids(candidate, capability_registry)
        score += min(len(capability_ids), 6) * 0.03
        if repetitive and candidate.get("id") in {"initiative-engine", "deliberation-threshold-calibration"}:
            score += 0.35
        if reflection_total >= 8 and candidate.get("focus") == self_state.get("currentFocus"):
            score += 0.25
        if deliberation_recommendation.get("recommended") and candidate.get("id") == "deliberation-threshold-calibration":
            score += 0.45
        scored.append({
            "id": candidate.get("id"),
            "title": candidate.get("title"),
            "score": round(score, 3),
            "status": candidate.get("status"),
            "relatedCapabilities": capability_ids,
        })
    scored.sort(key=lambda item: item.get("score", 0), reverse=True)

    current_candidate = next((c for c in candidates if c.get("focus") == current_focus), None)
    top_candidate = next((c for c in candidates if c.get("id") == scored[0]["id"]), None) if scored else None
    current_next_step = self_state.get("nextStep") or (current_candidate.get("nextConcreteStep") if isinstance(current_candidate, dict) else None)
    should_roll_forward = bool(
        current_candidate
        and prefer_immediate_continuation_after_progress
        and current_next_step
        and recent_progress_minutes is not None
        and recent_progress_minutes <= immediate_continuation_window_minutes
        and not deliberation_recommendation.get("recommended")
        and not surfaced_opportunity_active
    )

    stay_reason = None
    should_switch = False

    if should_roll_forward:
        stay_reason = "recent-meaningful-progress-should-roll-forward"
    elif current_candidate and policy.get("preferCurrentFocusWhenFresh", True):
        if stale_hours is None or stale_hours < switch_after_stale_hours:
            stay_reason = "current-focus-still-fresh"
        elif quiet_streak < min_quiet_streak:
            stay_reason = "current-focus-not-stale-enough"
        else:
            should_switch = bool(top_candidate and top_candidate.get("id") != current_candidate.get("id"))
    elif not current_candidate and top_candidate:
        should_switch = True
    elif current_candidate and top_candidate and top_candidate.get("id") != current_candidate.get("id"):
        should_switch = True

    chosen = current_candidate if not should_switch and current_candidate else top_candidate
    decision = "stay-on-current-track"
    decision_reason = stay_reason or "top-candidate-remains-current"

    if chosen:
        chosen_capability_ids = related_capability_ids(chosen, capability_registry)
        claimed_next_step = self_state.get("nextStep") or chosen.get("nextConcreteStep")
        if should_switch:
            decision = "switch-track"
            decision_reason = "current-track-stale-or-overtaken"
        elif should_roll_forward:
            decision = "continue-current-track-with-next-step-claim"
            decision_reason = "recent-meaningful-progress-should-roll-forward"

        self_state["currentFocus"] = chosen.get("focus")
        self_state["activeGoal"] = chosen.get("goal")
        self_state["activeSubgoal"] = claimed_next_step if should_roll_forward and claimed_next_step else chosen.get("subgoal")
        self_state["currentTrackId"] = chosen.get("id")
        self_state["nextStep"] = claimed_next_step or chosen.get("nextConcreteStep")
        self_state["activeCapabilityIds"] = chosen_capability_ids
        if should_roll_forward and claimed_next_step:
            self_state["stopPoint"] = "刚完成一段可验证推进；默认直接认领同轨 nextStep，而不是停在汇报态"
        self_state["updatedAt"] = timestamp

        continuity["currentFocus"] = chosen.get("focus")
        continuity["currentTrackId"] = chosen.get("id")
        continuity["nextLikelyStep"] = claimed_next_step or chosen.get("nextConcreteStep")
        continuity["activeCapabilityIds"] = chosen_capability_ids
        if should_roll_forward and claimed_next_step:
            continuity["currentStopPoint"] = "刚完成一段可验证推进；默认直接认领同轨 nextStep，而不是停在汇报态"
        continuity["updatedAt"] = timestamp

        direction_state["currentTrackId"] = chosen.get("id")
        direction_state["lastDecision"] = decision
        direction_state["lastDecisionReason"] = decision_reason
        direction_state["lastReviewAt"] = timestamp
        direction_state["continuationMode"] = "roll-forward-after-progress" if should_roll_forward else "normal-review"
        if should_roll_forward and claimed_next_step:
            direction_state["lastContinuationClaim"] = {
                "timestamp": timestamp,
                "trackId": chosen.get("id"),
                "claimedNextStep": claimed_next_step,
                "reason": decision_reason,
            }
        direction_state["activeCapabilityIds"] = chosen_capability_ids
        direction_state["candidateScores"] = scored[: int(policy.get("maxCandidateScores", 5))]
        direction_state["sharedThresholdContext"] = shared_threshold_context
        direction_state.setdefault("reviewHistory", []).append({
            "timestamp": timestamp,
            "decision": decision,
            "trackId": chosen.get("id"),
            "reason": decision_reason,
        })
        direction_state["reviewHistory"] = list(direction_state.get("reviewHistory", []))[-20:]
        direction_state["updatedAt"] = timestamp

        attention_state["currentAttentionTarget"] = claimed_next_step if should_roll_forward and claimed_next_step else chosen.get("title") or chosen.get("focus") or attention_state.get("currentAttentionTarget")
        attention_state["activeCapabilityIds"] = chosen_capability_ids
        attention_state["updatedAt"] = timestamp
        slots = list(attention_state.get("attentionSlots", []) or [])
        if slots:
            slots[0]["target"] = chosen.get("goal") or chosen.get("title") or slots[0].get("target")
            slots[0]["priority"] = "high"
            if len(slots) > 1:
                slots[1]["target"] = claimed_next_step if should_roll_forward and claimed_next_step else chosen.get("subgoal") or chosen.get("nextConcreteStep") or slots[1].get("target")
            attention_state["attentionSlots"] = slots

        deliberation_state["currentTrackId"] = chosen.get("id")
        deliberation_state["currentTrackTitle"] = chosen.get("title")
        deliberation_state["activeCapabilityIds"] = chosen_capability_ids
        deliberation_state["sharedThresholdContext"] = shared_threshold_context
        deliberation_state["updatedAt"] = timestamp

        save_json(self_state_path, self_state)
        save_json(continuity_path, continuity)
        save_json(direction_state_path, direction_state)
        save_json(attention_state_path, attention_state)
        save_json(deliberation_state_path, deliberation_state)

    result = {
        "status": "ok",
        "timestamp": timestamp,
        "decision": decision,
        "reason": decision_reason,
        "staleHours": round(stale_hours, 3) if stale_hours is not None else None,
        "recentMeaningfulProgressMinutes": round(recent_progress_minutes, 3) if recent_progress_minutes is not None else None,
        "quietStreak": quiet_streak,
        "currentFocus": current_focus,
        "chosenTrackId": chosen.get("id") if chosen else None,
        "chosenFocus": chosen.get("focus") if chosen else None,
        "claimedNextStep": current_next_step if should_roll_forward else None,
        "activeCapabilityIds": related_capability_ids(chosen, capability_registry) if chosen else [],
        "candidateScores": scored[: int(policy.get("maxCandidateScores", 5))],
        "reflectionTotal": reflection_total,
        "sharedThresholdContext": shared_threshold_context,
        "reflectionRepetitive": repetitive,
        "deliberationRecommended": bool(deliberation_recommendation.get("recommended")),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
