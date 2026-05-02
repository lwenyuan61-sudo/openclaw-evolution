from __future__ import annotations

import argparse
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
UPGRADE_PATH = AUTO / "upgrade-state.json"
WORLD_PATH = CORE / "world-state.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default or {})
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def parse_iso(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return None


def hours_since(value: Any) -> float | None:
    parsed = parse_iso(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc).astimezone() - parsed).total_seconds() / 3600.0


def recent_action_repetition(runtime: dict[str, Any]) -> tuple[str | None, int]:
    actions = []
    for item in as_list(runtime.get("actions")):
        if not isinstance(item, dict):
            continue
        if item.get("action") == "resident-action":
            parsed = None
            stdout = item.get("stdout")
            if isinstance(stdout, str):
                try:
                    parsed = json.loads(stdout)
                except Exception:
                    parsed = None
            if isinstance(parsed, dict):
                selected = parsed.get("selectedAction") or parsed.get("review", {}).get("selectedAction")
                if selected:
                    actions.append(str(selected))
    if not actions:
        return None, 0
    last = actions[-1]
    count = 0
    for action in reversed(actions):
        if action != last:
            break
        count += 1
    return last, count


def completed_connector_ids(upgrade: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    last = upgrade.get("lastConnectorCompleted")
    if isinstance(last, dict) and last.get("id"):
        ids.add(str(last.get("id")))
    verification = upgrade.get("lastVerification")
    if isinstance(verification, dict) and verification.get("status") == "ok" and verification.get("selected"):
        ids.add(str(verification.get("selected")))
    for item in as_list(upgrade.get("completedConnectors")):
        if isinstance(item, dict) and item.get("id"):
            ids.add(str(item.get("id")))
        elif item:
            ids.add(str(item))
    return ids


def active_goal_pressure(goal_register: dict[str, Any], upgrade: dict[str, Any]) -> tuple[float, list[str]]:
    completed = completed_connector_ids(upgrade)
    candidates = []
    for item in as_list(goal_register.get("candidates")):
        if not isinstance(item, dict) or item.get("status") not in {"active", "queued"}:
            continue
        goal_id = str(item.get("id") or "")
        # A goal can remain long-lived/active while its current drive-backed
        # connector is already durable-completed. Do not let those completed
        # goal connectors keep generating homeostatic pressure and false
        # drive-stall handoffs.
        if goal_id and (
            "advance-homeostatic-drive-goal-" + goal_id in completed
            or "advance-" + goal_id in completed
            or goal_id in completed
        ):
            continue
        candidates.append(item)
    if not candidates:
        return 0.0, []
    scored = []
    for item in candidates:
        lee = float(item.get("leeValue", 0.5) or 0.5)
        leverage = float(item.get("learningLeverage", 0.5) or 0.5)
        risk = float(item.get("noiseRisk", 0.2) or 0.2)
        score = clamp((lee + leverage) / 2.0 - risk * 0.25)
        scored.append((score, str(item.get("id") or "unknown-goal")))
    scored.sort(reverse=True)
    top = scored[:5]
    return clamp(sum(s for s, _ in top) / max(1, len(top))), [gid for _, gid in top]


def compute_drive() -> dict[str, Any]:
    timestamp = now_iso()
    homeostasis = load_json(CORE / "homeostasis.json")
    world = load_json(WORLD_PATH)
    upgrade = load_json(UPGRADE_PATH)
    goals = load_json(AUTO / "goal-register.json")
    learning = load_json(CORE / "learning-state.json")
    procedural = load_json(CORE / "procedural-memory.json")
    runtime = load_json(STATE / "resident_runtime.json")
    reflection = load_json(STATE / "resident_reflection.json")
    consistency = load_json(STATE / "consistency_report.json")
    opportunity = load_json(STATE / "lee_opportunity_review.json")
    handoff = load_json(STATE / "persona_deliberation_handoff.json")

    belief = world.get("beliefState", {}) if isinstance(world.get("beliefState"), dict) else {}
    predictions = as_list(world.get("predictions"))
    current_experiment = upgrade.get("currentExperiment", {}) if isinstance(upgrade.get("currentExperiment"), dict) else {}
    chosen = current_experiment.get("chosenCandidate", {}) if isinstance(current_experiment.get("chosenCandidate"), dict) else {}
    current_selected = str(chosen.get("id") or "")
    info = upgrade.get("informationScout", {}) if isinstance(upgrade.get("informationScout"), dict) else {}
    web = info.get("webScout", {}) if isinstance(info.get("webScout"), dict) else {}
    cadence = upgrade.get("internalizedCadence", {}) if isinstance(upgrade.get("internalizedCadence"), dict) else {}
    cadence_pressure = cadence.get("lastCadencePressure", {}) if isinstance(cadence.get("lastCadencePressure"), dict) else {}
    counters = learning.get("counters", {}) if isinstance(learning.get("counters"), dict) else {}

    low_value_ticks = safe_int(belief.get("recentLowValueMaintenanceTicks"), 0)
    s2_debt = safe_int(belief.get("s2CompileDebt"), 0)
    verified = safe_int(counters.get("deliberationEpisodesVerified"), 0)
    compiled = safe_int(counters.get("deliberationPatternsCompiled"), 0)
    covered_by_s1 = safe_int(counters.get("deliberationEpisodesCoveredByS1"), 0)
    for collection in (as_list(procedural.get("habits")) + as_list(procedural.get("deliberationPatterns"))):
        if not isinstance(collection, dict):
            continue
        stats = collection.get("stats", {}) if isinstance(collection.get("stats"), dict) else {}
        covered_by_s1 = max(
            covered_by_s1,
            len(as_list(collection.get("episodeIds"))),
            safe_int(stats.get("verified"), 0),
            safe_int(stats.get("success"), 0) if collection.get("preferredAction") in {"silent-wait", "continue-focus"} else 0,
        )
    learning_debt_raw = max(s2_debt, verified - max(compiled, covered_by_s1))
    no_candidate_streak = safe_int(web.get("noCandidateStreak"), 0)
    generated_goals = safe_int(web.get("generatedGoals"), 0)
    recent_signals = safe_int(belief.get("recentSignalCount"), 0)
    failed_actions = [a for a in as_list(runtime.get("actions")) if isinstance(a, dict) and safe_int(a.get("rc"), 0) != 0]
    last_action, repeat_count = recent_action_repetition(runtime)
    goal_pressure, top_goal_ids = active_goal_pressure(goals, upgrade)

    low_value_prediction = any(isinstance(p, dict) and p.get("id") == "low-value-maintenance-loop" for p in predictions)
    high_ranked_goal = bool(top_goal_ids)
    quiet_hours = str(belief.get("mode") or "") == "quiet-hours"
    interruption_cost = 0.75 if quiet_hours else 0.35
    if homeostasis.get("proactiveTouchPolicy", {}).get("preferSilentProgress"):
        interruption_cost += 0.1
    interruption_cost = clamp(interruption_cost)

    maintenance_fatigue = clamp((low_value_ticks / 8.0) + (0.25 if current_selected == "maintain-current-upgrade-loop" else 0.0) + (0.15 if last_action in {"continue-focus", "silent-wait"} and repeat_count >= 2 else 0.0))
    novelty_drive = clamp((generated_goals * 0.35) + (recent_signals * 0.15) + (no_candidate_streak / 12.0))
    prediction_error_drive = clamp((0.45 if low_value_prediction else 0.0) + (0.15 if recent_signals else 0.0) + (0.2 if consistency.get("status") in {"warning", "error"} else 0.0))
    learning_debt = clamp(learning_debt_raw / 8.0)
    failure_drive = clamp(len(failed_actions) / 3.0)
    goal_drive = clamp(goal_pressure)
    last_user_hours = hours_since(cadence.get("lastUserInteractionAt"))
    conversation_need = clamp(((last_user_hours or 0.0) / 8.0) * 0.35)
    help_need = clamp(goal_drive * 0.55 + maintenance_fatigue * 0.25 + prediction_error_drive * 0.2)
    prepared_report_need = 0.35 if handoff.get("visibleDeliveryRequired") or handoff.get("reportPreparedForLee") else 0.0
    opportunity_need = 0.25 if opportunity.get("decision", {}).get("shouldSurface") or opportunity.get("valueSignal", {}).get("detected") else 0.0
    lee_service_drive = clamp(conversation_need + help_need + prepared_report_need + opportunity_need)
    # This is a service/affiliation drive, not a license to interrupt. During
    # quiet-hours it should mostly convert into prepared help and better next
    # actions, while surface decisions still go through interruption cost.
    arousal = clamp((maintenance_fatigue * 0.22) + (novelty_drive * 0.16) + (prediction_error_drive * 0.2) + (learning_debt * 0.14) + (failure_drive * 0.1) + (goal_drive * 0.14) + (lee_service_drive * 0.12))

    reasons: list[str] = []
    if low_value_prediction:
        reasons.append("world-model predicts low-value maintenance loop")
    if maintenance_fatigue >= 0.55:
        reasons.append(f"maintenance fatigue high: lowValueTicks={low_value_ticks}, selected={current_selected or 'none'}")
    if no_candidate_streak >= 4:
        reasons.append(f"web scout no-candidate streak={no_candidate_streak}")
    if generated_goals:
        reasons.append(f"web scout generated {generated_goals} goal(s)")
    if learning_debt >= 0.35:
        reasons.append(f"learning debt present: verified={verified}, compiled={compiled}, coveredByS1={covered_by_s1}, worldDebt={s2_debt}")
    if failure_drive:
        reasons.append(f"resident action failures detected={len(failed_actions)}")
    if quiet_hours:
        reasons.append("quiet-hours increases interruption cost")
    if high_ranked_goal:
        reasons.append("active/queued high-value goals exist: " + ", ".join(top_goal_ids[:3]))
    if lee_service_drive >= 0.45:
        reasons.append(
            "Lee-service drive active: wants useful contact/help but must respect interruption cost "
            f"(conversationNeed={round(conversation_need, 3)}, helpNeed={round(help_need, 3)})"
        )
    if not reasons:
        reasons.append("all drives within maintenance band")

    recommended_mode = "maintain"
    connector_bias = "upgrade-state -> continuity-state"
    should_surface = False
    if (
        failure_drive >= 0.5
        or (maintenance_fatigue >= 0.8 and goal_drive >= 0.75 and low_value_prediction)
        or (arousal >= 0.62 and (maintenance_fatigue >= 0.5 or novelty_drive >= 0.45 or prediction_error_drive >= 0.5))
    ):
        recommended_mode = "upgrade-now"
        connector_bias = "homeostaticDrive -> autonomy_info_scout -> autonomy_upgrade_tick"
    elif novelty_drive >= 0.45 or no_candidate_streak >= 5:
        recommended_mode = "read-only-scout"
        connector_bias = "homeostaticDrive -> autonomy_web_scout -> goal-register"
    elif learning_debt >= 0.5:
        recommended_mode = "compile-learning"
        connector_bias = "homeostaticDrive -> learning_update -> procedural-memory"
    elif lee_service_drive >= 0.62 and interruption_cost >= 0.7:
        recommended_mode = "prepare-help"
        connector_bias = "leeServiceDrive -> opportunity-routing -> prepare useful help silently"
    elif lee_service_drive >= 0.72 and interruption_cost < 0.7:
        recommended_mode = "seek-helpful-contact"
        connector_bias = "leeServiceDrive -> lee-opportunity-routing -> brief useful check-in"
    elif goal_drive >= 0.7 and arousal >= 0.45:
        recommended_mode = "continue-focus"
        connector_bias = "goal-register -> initiative_review -> smallest-safe-action"
    if arousal >= 0.85 and interruption_cost <= 0.55 and (failure_drive >= 0.5 or generated_goals > 0 or lee_service_drive >= 0.8):
        should_surface = True

    drive = {
        "timestamp": timestamp,
        "arousal": round(arousal, 3),
        "noveltyDrive": round(novelty_drive, 3),
        "predictionErrorDrive": round(prediction_error_drive, 3),
        "maintenanceFatigue": round(maintenance_fatigue, 3),
        "interruptionCost": round(interruption_cost, 3),
        "learningDebt": round(learning_debt, 3),
        "failureDrive": round(failure_drive, 3),
        "goalDrive": round(goal_drive, 3),
        "leeServiceDrive": round(lee_service_drive, 3),
        "conversationNeed": round(conversation_need, 3),
        "helpNeed": round(help_need, 3),
        "recommendedMode": recommended_mode,
        "recommendedConnectorBias": connector_bias,
        "shouldSurfaceToLee": should_surface,
        "reasons": reasons,
        "evidence": {
            "recentLowValueMaintenanceTicks": low_value_ticks,
            "currentSelected": current_selected or None,
            "lastResidentAction": last_action,
            "lastResidentActionRepeatCount": repeat_count,
            "noCandidateStreak": no_candidate_streak,
            "generatedGoals": generated_goals,
            "recentSignalCount": recent_signals,
            "learningDebtRaw": learning_debt_raw,
            "coveredByS1": covered_by_s1,
            "failedActionCount": len(failed_actions),
            "lastUserInteractionHours": round(last_user_hours, 3) if last_user_hours is not None else None,
            "preparedReportNeed": prepared_report_need,
            "opportunityNeed": opportunity_need,
            "topGoalIds": top_goal_ids[:5],
            "cadencePressure": cadence_pressure,
            "reflectionTotal": reflection.get("totalScore") if isinstance(reflection, dict) else None,
        },
        "policy": {
            "advisoryOnly": True,
            "boundedDrives": True,
            "noExternalWrites": True,
            "quietHoursSurfaceRequiresHighArousalAndLowInterruptionCost": True,
            "leeServiceDriveIsProSocialNotManipulative": True,
            "contactDesireMustConvertToHelpOrRespectfulCheckIn": True,
        },
    }
    return drive


def apply_drive(drive: dict[str, Any]) -> None:
    upgrade = load_json(UPGRADE_PATH, {})
    upgrade["homeostaticDrive"] = drive
    upgrade.setdefault("connectionPolicy", {})["homeostaticDriveArbiter"] = {
        "enabled": True,
        "script": "core/scripts/homeostatic_drive_arbiter.py",
        "advisoryOnly": True,
        "influences": ["autonomy_info_scout", "autonomy_internal_cadence", "goal routing"],
    }
    if drive.get("recommendedMode") in {"upgrade-now", "compile-learning"}:
        internal = upgrade.setdefault("internalizedCadence", {})
        internal["forceUpgradeRequestedAt"] = drive.get("timestamp")
        internal["forceUpgradeReason"] = "homeostatic-drive:" + str(drive.get("recommendedMode"))
    upgrade["updatedAt"] = drive.get("timestamp") or now_iso()
    save_json(UPGRADE_PATH, upgrade)

    world = load_json(WORLD_PATH, {})
    world["homeostaticDriveSummary"] = {
        "timestamp": drive.get("timestamp"),
        "arousal": drive.get("arousal"),
        "recommendedMode": drive.get("recommendedMode"),
        "recommendedConnectorBias": drive.get("recommendedConnectorBias"),
        "topReasons": as_list(drive.get("reasons"))[:3],
    }
    candidates = as_list(world.get("actionCandidates"))
    candidates = [c for c in candidates if not (isinstance(c, dict) and c.get("action") == "follow-homeostatic-drive")]
    candidates.insert(0, {
        "action": "follow-homeostatic-drive",
        "expectedOutcome": "use bounded biological-style drive pressures to break stale maintenance loops without becoming noisy",
        "cost": "low",
        "risk": "low-internal-advisory",
        "when": "homeostaticDrive.recommendedMode is not maintain",
        "recommendedMode": drive.get("recommendedMode"),
    })
    world["actionCandidates"] = candidates[:8]
    world["timestamp"] = drive.get("timestamp") or now_iso()
    save_json(WORLD_PATH, world)

    append_jsonl(LOG_PATH, {
        "id": "homeostatic-drive-" + str(drive.get("timestamp")),
        "timestamp": drive.get("timestamp"),
        "type": "homeostatic-drive-arbiter",
        "status": "advisory-written",
        "recommendedMode": drive.get("recommendedMode"),
        "arousal": drive.get("arousal"),
        "reasons": as_list(drive.get("reasons"))[:5],
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    drive = compute_drive()
    if not args.dry_run:
        apply_drive(drive)
    print(json.dumps({"ok": True, "dryRun": bool(args.dry_run), "homeostaticDrive": drive}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
