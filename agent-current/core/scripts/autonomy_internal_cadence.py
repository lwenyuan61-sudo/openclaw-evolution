from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
UPGRADE_PATH = AUTO / "upgrade-state.json"
HANDOFF_PATH = STATE / "persona_deliberation_handoff.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def run_python(script: Path, *args: str) -> tuple[int, str, str, dict[str, Any] | None]:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    parsed = None
    if proc.stdout.strip():
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            parsed = None
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip(), parsed


def pending_handoff_active() -> bool:
    handoff = load_json(HANDOFF_PATH, {})
    return bool(handoff.get("pending") and not handoff.get("handledAt"))


def derive_dynamic_interval_seconds(upgrade: dict[str, Any], learning: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    internal = upgrade.get("internalizedCadence", {}) if isinstance(upgrade.get("internalizedCadence"), dict) else {}
    adaptive = internal.get("adaptiveTiming", {}) if isinstance(internal.get("adaptiveTiming"), dict) else {}
    base = float(internal.get("upgradeIntervalSeconds", 420) or 420)
    minimum = float(adaptive.get("minIntervalSeconds", 180) or 180)
    maximum = float(adaptive.get("maxIntervalSeconds", 1800) or 1800)
    counters = learning.get("counters", {}) if isinstance(learning.get("counters"), dict) else {}
    metrics = upgrade.get("metrics", {}) if isinstance(upgrade.get("metrics"), dict) else {}
    blockers = upgrade.get("blockers", []) if isinstance(upgrade.get("blockers"), list) else []
    deferred = upgrade.get("deferredDecisions", []) if isinstance(upgrade.get("deferredDecisions"), list) else []

    verified = int(counters.get("deliberationEpisodesVerified", 0) or 0)
    compiled = int(counters.get("deliberationPatternsCompiled", 0) or 0)
    selected = int(metrics.get("experimentsSelected", 0) or 0)
    verified_exp = int(metrics.get("experimentsVerified", 0) or 0)

    pressure = 0.0
    reasons: list[str] = []
    if verified - compiled >= 4:
        pressure += 0.25
        reasons.append("s2-verified-exceeds-compiled")
    if selected > verified_exp:
        pressure += 0.2
        reasons.append("selected-experiments-await-verification")
    if upgrade.get("creativeGoalSynthesis", {}).get("generatedCount"):
        pressure += 0.2
        reasons.append("creative-goals-generated")
    if blockers or deferred:
        pressure -= 0.2
        reasons.append("has-blockers-or-deferred-decisions")
    if pending_handoff_active():
        pressure -= 0.45
        reasons.append("handoff-already-pending")

    pressure = max(-0.6, min(0.8, pressure))
    interval = base * (1.0 - pressure)
    interval = max(minimum, min(maximum, interval))
    return interval, {
        "baseIntervalSeconds": base,
        "dynamicIntervalSeconds": round(interval, 3),
        "pressure": round(pressure, 3),
        "reasons": reasons or ["baseline"],
        "minIntervalSeconds": minimum,
        "maxIntervalSeconds": maximum,
    }


def build_handoff(timestamp: str, tick_result: dict[str, Any]) -> dict[str, Any]:
    selected = tick_result.get("selected", {}) if isinstance(tick_result, dict) else {}
    selected_id = selected.get("id") or "unknown-connector"
    minimal_action = selected.get("minimalAction") or "继续选择一个最小高价值连接器"
    return {
        "pending": True,
        "createdAt": timestamp,
        "reason": "resident-internal-autonomy-upgrade-due",
        "currentTrackId": "autonomy-self-upgrade-manager",
        "question": "持续自主升级已到期：请the agent本人格接手，完成一个高价值 integration-over-creation 连接器，并把结果汇报 Lee。",
        "summary": (
            "resident 内化节奏已判断进入持续升级窗口；cron 只保留为禁用兜底，不再决定升级节奏。"
            f" 当前候选连接器：{selected_id}；建议最小动作：{minimal_action}。"
        ),
        "shouldReportToLee": True,
        "leeReportRecommendation": {
            "shouldReportToLee": True,
            "reason": "Lee 要求每次自主升级结果用 WhatsApp 汇报；该 wake 来自内化 resident cadence。",
        },
        "contextFiles": [
            "autonomy/upgrade-state.json",
            "autonomy/experiment-log.jsonl",
            "core/self-state.json",
            "autonomy/continuity-state.json",
            "core/agency-loop.md",
            "core/scripts/autonomy_upgrade_tick.py",
        ],
        "autonomyTickResult": tick_result,
    }


def reportable_verified_progress(upgrade: dict[str, Any]) -> dict[str, Any] | None:
    verification = upgrade.get("lastVerification")
    if not isinstance(verification, dict):
        return None
    if verification.get("status") != "ok":
        return None
    if verification.get("reportedToLee") or verification.get("progressReportRequestedAt"):
        return None
    selected = str(verification.get("selected") or verification.get("id") or "")
    if not selected or selected == "maintain-current-upgrade-loop":
        return None
    # Not every verified internal cleanup is Lee-facing progress.  Repeated
    # quiet-hours reports about classifier/benign-maintain/cleanup writebacks
    # created notification noise and then handoff state churn.  These are still
    # durable progress, but they should be compiled into state and surfaced only
    # if they fail, create a blocker, or Lee asks.
    quiet_internal_prefixes = (
        "semantic-freshness-benign-maintain-classifier",
        "advance-semantic-freshness-benign-maintain-classifier",
        "screen-semantic-durable-writeback",
        "advance-screen-semantic-durable-writeback",
        "visible-delivery-reconciliation-",
        "quiet-internal-report-suppression-policy",
        "advance-quiet-internal-report-suppression-policy",
    )
    quiet_internal_contains = (
        "quiet-report" in selected
        or "benign-maintain" in selected
        or "durable-writeback" in selected
        or "context-pressure" in selected
        or "semantic-bottleneck" in selected
        or "memory-warning" in selected
        or "resource-pressure" in selected
    )
    if selected.startswith(quiet_internal_prefixes) or quiet_internal_contains:
        verification["reportedToLee"] = False
        verification["reportSuppressedAt"] = now_iso()
        verification["reportSuppressionReason"] = "quiet-internal-maintenance-connector-not-lee-facing-unless-failed-or-blocked"
        return None
    return verification


def build_verified_progress_handoff(timestamp: str, verification: dict[str, Any]) -> dict[str, Any]:
    selected = str(verification.get("selected") or verification.get("id") or "verified-connector")
    verified_at = verification.get("verifiedAt") or verification.get("timestamp") or timestamp
    gate_count = len(verification.get("gates", []) or [])
    summary = (
        "已验证的自主升级进展尚未被当前节奏显式上报；quiet-hours 只能降低打扰长度，"
        f"不能吞掉 verified progress。连接器：{selected}；验证时间：{verified_at}；验证门数量：{gate_count}。"
    )
    return {
        "pending": True,
        "createdAt": timestamp,
        "reason": "verified-autonomy-progress-needs-brief-report",
        "currentTrackId": "autonomy-self-upgrade-manager",
        "question": "请the agent本人格接手：把这次已验证的自主升级进展用一条低打扰短讯汇报 Lee，然后回写 reportedToLee。",
        "summary": summary,
        "shouldReportToLee": True,
        "leeReportRecommendation": {
            "shouldReportToLee": True,
            "reason": "verified-progress-overrides-quiet-hours-suppression",
            "style": "brief-low-disturbance",
            "summary": summary,
        },
        "contextFiles": [
            "autonomy/upgrade-state.json",
            "autonomy/experiment-log.jsonl",
            "memory/2026-04-26.md",
            "heartbeat.md",
        ],
        "verifiedProgress": verification,
    }


def main() -> None:
    timestamp = now_iso()
    upgrade = load_json(UPGRADE_PATH, {})
    learning = load_json(CORE / "learning-state.json", {})
    internal = upgrade.setdefault("internalizedCadence", {})
    internal.setdefault("enabled", True)
    internal.setdefault("mode", "standby-until-quiet-or-user-request")
    internal.setdefault("quietWindowMinutes", 30)
    internal.setdefault("upgradeIntervalSeconds", 420)
    internal.setdefault("priority", "high-value-final-form-alignment-first")
    internal.setdefault("cronRole", "disabled-fallback-wake-carrier-only")
    internal.setdefault("adaptiveTiming", {
        "enabled": True,
        "minIntervalSeconds": 180,
        "maxIntervalSeconds": 1800,
        "principle": "value pressure shortens cadence; blockers/noise lengthen cadence; no fixed dead timer owns autonomy",
    })

    if not internal.get("enabled", True):
        result = {"status": "disabled", "timestamp": timestamp}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    last_user_at = parse_iso(internal.get("lastUserInteractionAt") or upgrade.get("quietActivationGate", {}).get("lastUserInteractionAt"))
    quiet_minutes = float(internal.get("quietWindowMinutes", 30) or 30)
    elapsed = (now() - last_user_at).total_seconds() / 60.0 if last_user_at else None
    explicit_active = bool(internal.get("explicitlyActivatedByLee"))
    quiet_ready = elapsed is None or elapsed >= quiet_minutes

    if not explicit_active and not quiet_ready:
        internal["mode"] = "standby-waiting-for-quiet-window"
        internal["lastDecision"] = {
            "timestamp": timestamp,
            "decision": "wait",
            "elapsedQuietMinutes": round(elapsed, 3) if elapsed is not None else None,
            "requiredQuietMinutes": quiet_minutes,
        }
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        result = {"status": "waiting", **internal["lastDecision"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    internal["mode"] = "active-continuous-upgrade"

    verified_progress = reportable_verified_progress(upgrade)
    if verified_progress and not pending_handoff_active():
        handoff = build_verified_progress_handoff(timestamp, verified_progress)
        save_json(HANDOFF_PATH, handoff)
        verified_progress["progressReportRequestedAt"] = timestamp
        verified_progress["reportedToLee"] = False
        verified_progress["reportPolicy"] = "verified-progress-overrides-quiet-hours-suppression"
        rc_dispatch, out_dispatch, err_dispatch, parsed_dispatch = run_python(
            CORE / "scripts" / "persona_handoff_dispatch.py",
            "--mode", "now",
            "--dedupe-minutes", "1",
            "--claim-stale-minutes", "20",
        )
        internal["lastDecision"] = {
            "timestamp": timestamp,
            "decision": "requested-verified-progress-report",
            "selected": verified_progress.get("selected") or verified_progress.get("id"),
            "dispatchReturncode": rc_dispatch,
            "reason": "verified progress should surface briefly instead of being suppressed by quiet-hours",
        }
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        append_jsonl(LOG_PATH, {
            "id": f"verified-progress-report-{timestamp}",
            "timestamp": timestamp,
            "type": "verified-progress-report-latch",
            "status": "handoff-requested" if rc_dispatch == 0 else "handoff-dispatch-warning",
            "selected": verified_progress.get("selected") or verified_progress.get("id"),
            "dispatch": parsed_dispatch or {"stdout": out_dispatch, "stderr": err_dispatch, "returncode": rc_dispatch},
            "principle": "verified autonomy progress surfaces briefly even during quiet-hours",
        })
        print(json.dumps({"status": "verified-progress-report-requested", **internal["lastDecision"]}, ensure_ascii=False, indent=2))
        return

    last_upgrade_at = parse_iso(internal.get("lastUpgradeAt"))
    adaptive_enabled = bool(internal.get("adaptiveTiming", {}).get("enabled", True)) if isinstance(internal.get("adaptiveTiming"), dict) else True
    if adaptive_enabled:
        interval_seconds, cadence_pressure = derive_dynamic_interval_seconds(upgrade, learning)
    else:
        interval_seconds = float(internal.get("upgradeIntervalSeconds", 420) or 420)
        cadence_pressure = {"baseIntervalSeconds": interval_seconds, "dynamicIntervalSeconds": interval_seconds, "pressure": 0.0, "reasons": ["adaptive-disabled"]}
    internal["lastCadencePressure"] = cadence_pressure
    due = last_upgrade_at is None or now() - last_upgrade_at >= timedelta(seconds=interval_seconds)

    scout_result: dict[str, Any] | None = None
    if not due:
        rc_scout, out_scout, err_scout, parsed_scout = run_python(CORE / "scripts" / "autonomy_info_scout.py")
        scout_result = parsed_scout or {"stdout": out_scout, "stderr": err_scout, "returncode": rc_scout}
        if isinstance(scout_result, dict) and scout_result.get("recommendedAction") == "upgrade-now":
            due = True
            cadence_pressure.setdefault("reasons", []).append("information-scout-upgrade-now")
            cadence_pressure["scoutOverride"] = True

    if not due:
        remaining = interval_seconds - (now() - last_upgrade_at).total_seconds() if last_upgrade_at else 0
        internal["lastDecision"] = {
            "timestamp": timestamp,
            "decision": "active-not-due-after-scout",
            "remainingSeconds": max(0, round(remaining, 3)),
            "cadencePressure": cadence_pressure,
            "informationScout": scout_result,
        }
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        result = {"status": "active-not-due", **internal["lastDecision"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if pending_handoff_active():
        internal["lastDecision"] = {
            "timestamp": timestamp,
            "decision": "defer-new-upgrade",
            "reason": "persona-handoff-already-pending",
        }
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        result = {"status": "deferred", **internal["lastDecision"]}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if scout_result is None:
        rc_scout, out_scout, err_scout, parsed_scout = run_python(CORE / "scripts" / "autonomy_info_scout.py")
        scout_result = parsed_scout or {"stdout": out_scout, "stderr": err_scout, "returncode": rc_scout}

    rc_synth, out_synth, err_synth, parsed_synth = run_python(CORE / "scripts" / "autonomy_goal_synthesizer.py")
    # Resident cadence is allowed to propose work, not execute autonomy work.
    # Non-maintenance connector selection/implementation must be pulled up to
    # the main persona for high-level reasoning and visible accountability.
    rc, stdout, stderr, parsed = run_python(CORE / "scripts" / "autonomy_upgrade_tick.py", "--dry-run")
    tick_result = parsed if isinstance(parsed, dict) else {"rawStdout": stdout, "stderr": stderr, "returncode": rc}
    tick_result["informationScout"] = scout_result
    tick_result["creativeGoalSynthesis"] = parsed_synth or {"stdout": out_synth, "stderr": err_synth, "returncode": rc_synth}

    # autonomy_upgrade_tick.py is intentionally called as --dry-run here. Older
    # versions let resident cadence select/write experiments directly, which
    # blurred the boundary between low-level proposing and high-level execution.
    # Reload anyway in case scouts/synthesizers updated shared state.
    upgrade = load_json(UPGRADE_PATH, upgrade)
    internal = upgrade.setdefault("internalizedCadence", {})

    selected = tick_result.get("selected", {}) if isinstance(tick_result, dict) else {}
    selected_id = selected.get("id") if isinstance(selected, dict) else None
    # A maintenance tick is useful bookkeeping, but it is explicitly not a
    # high-value connector. Do not wake the main persona or Lee just to report
    # “nothing new”; wait for a real connector/fresh gap instead.
    if selected_id == "maintain-current-upgrade-loop":
        scout_drive = scout_result.get("homeostaticDrive", {}) if isinstance(scout_result, dict) and isinstance(scout_result.get("homeostaticDrive"), dict) else {}
        scout_findings = scout_result.get("findings", []) if isinstance(scout_result, dict) and isinstance(scout_result.get("findings"), list) else []
        high_findings = [item for item in scout_findings if isinstance(item, dict) and item.get("severity") == "high"]
        lee_review = load_json(STATE / "lee_opportunity_review.json", {})
        reach_out_gate = lee_review.get("reachOutGate", {}) if isinstance(lee_review.get("reachOutGate"), dict) else {}
        # A scout-level upgrade-now can be produced by two medium watch signals.
        # If all drive-backed goals are completed and the selector returns
        # maintain, that may be convergence. But Lee-service pressure is a
        # separate boundary: resident may prepare, not decide how to help Lee.
        drive_mode = scout_drive.get("recommendedMode")
        service_mode = reach_out_gate.get("driveRecommendedMode") or drive_mode
        try:
            service_drive = float(reach_out_gate.get("leeServiceDrive", scout_drive.get("leeServiceDrive", 0.0)) or 0.0)
        except (TypeError, ValueError):
            service_drive = 0.0
        service_decision = reach_out_gate.get("decision")
        last_service_handoff = parse_iso(internal.get("lastLeeServiceHandoffAt"))
        service_cooldown_minutes = float(internal.get("leeServiceHandoffCooldownMinutes", 90) or 90)
        service_cooldown_elapsed = last_service_handoff is None or now() - last_service_handoff >= timedelta(minutes=service_cooldown_minutes)
        service_needs_main_persona = (
            service_drive >= 0.9
            and service_mode in {"prepare-help", "seek-helpful-contact"}
            and service_decision in {"prepare-help-silently", None}
            and service_cooldown_elapsed
        )
        # Only hard upgrade/compile modes imply a broken drive->candidate chain
        # when the selector returns maintenance. read-only-scout is often a
        # healthy curiosity/quality-gate pressure; service/contact modes now
        # get a bounded main-persona handoff instead of remaining silent forever.
        drive_requires_main_persona = drive_mode in {"upgrade-now", "compile-learning"}
        read_only_scout_escalates = drive_mode == "read-only-scout" and bool(high_findings)
        drive_wants_upgrade = drive_requires_main_persona or read_only_scout_escalates or bool(high_findings) or service_needs_main_persona
        if drive_wants_upgrade:
            reason = "homeostatic-drive-stalled-on-maintain"
            question = "内部驱动层反复要求 upgrade-now，但 autonomy_upgrade_tick 仍选择 maintain-current-upgrade-loop。请the agent本人格接手，判断为什么驱动压力没有变成真实 connector，并执行一个安全的最小修复。"
            summary = (
                "homeostaticDrive / informationScout 已给出升级压力，但候选选择器只返回维护项。"
                "这说明 drive -> candidate -> handoff 链路存在断点，不能继续静默维护。"
            )
            if service_needs_main_persona:
                reason = "lee-service-drive-needs-main-persona"
                question = "Lee-service drive 表示需要准备帮助或进行有用联系；请the agent本人格接手，判断 Lee 现在最可能需要什么，并执行一个安全、可逆、低打扰的最小帮助动作或形成可见简短汇报。"
                summary = (
                    "resident 只能感知和准备，不能替代the agent本人格决定如何帮助 Lee 或是否联系 Lee。"
                    f" 当前 service drive={service_drive}, mode={service_mode}, gate={service_decision}，"
                    "必须交给高层判断，而不是长期静默准备。"
                )
            handoff = {
                "pending": True,
                "createdAt": timestamp,
                "reason": reason,
                "currentTrackId": "autonomy-self-upgrade-manager",
                "question": question,
                "summary": summary,
                "shouldReportToLee": True,
                "leeReportRecommendation": {
                    "shouldReportToLee": True,
                    "reason": "涉及帮助 Lee / 联系 Lee / 系统自升级执行，必须由 main persona 高层判断和执行，不应由 resident 静默完成。",
                    "style": "brief-after-fix-or-clear-blocker",
                },
                "contextFiles": [
                    "autonomy/upgrade-state.json",
                    "autonomy/experiment-log.jsonl",
                    "core/scripts/homeostatic_drive_arbiter.py",
                    "core/scripts/autonomy_info_scout.py",
                    "core/scripts/autonomy_upgrade_tick.py",
                    "core/scripts/autonomy_internal_cadence.py",
                    "state/lee_opportunity_review.json",
                ],
                "autonomyTickResult": tick_result,
                "informationScout": scout_result,
                "homeostaticDrive": scout_drive,
                "reachOutGate": reach_out_gate,
            }
            save_json(HANDOFF_PATH, handoff)
            rc_dispatch, out_dispatch, err_dispatch, parsed_dispatch = run_python(
                CORE / "scripts" / "persona_handoff_dispatch.py",
                "--mode", "now",
                "--dedupe-minutes", "1",
                "--claim-stale-minutes", "20",
            )
            internal["lastUpgradeAt"] = timestamp
            if service_needs_main_persona:
                internal["lastLeeServiceHandoffAt"] = timestamp
            internal["lastDecision"] = {
                "timestamp": timestamp,
                "decision": "requested-lee-service-handoff" if service_needs_main_persona else "requested-drive-stall-handoff",
                "selected": selected_id,
                "driveRecommendedMode": scout_drive.get("recommendedMode"),
                "serviceDrive": service_drive,
                "serviceMode": service_mode,
                "dispatchReturncode": rc_dispatch,
                "reason": "Lee-service pressure requires main persona judgment" if service_needs_main_persona else "drive pressure requested upgrade but candidate selector returned maintain",
            }
            metrics = upgrade.setdefault("metrics", {})
            metrics["internalCadenceUpgradeRequests"] = int(metrics.get("internalCadenceUpgradeRequests", 0) or 0) + 1
            upgrade["updatedAt"] = timestamp
            save_json(UPGRADE_PATH, upgrade)
            append_jsonl(LOG_PATH, {
                "id": f"drive-stall-handoff-{timestamp}",
                "timestamp": timestamp,
                "type": "lee-service-drive-main-persona-handoff" if service_needs_main_persona else "homeostatic-drive-stall-handoff",
                "status": "handoff-requested" if rc_dispatch == 0 else "handoff-dispatch-warning",
                "selected": selected_id,
                "driveRecommendedMode": scout_drive.get("recommendedMode"),
                "serviceDrive": service_drive,
                "serviceMode": service_mode,
                "dispatch": parsed_dispatch or {"stdout": out_dispatch, "stderr": err_dispatch, "returncode": rc_dispatch},
                "principle": "Lee-service pressure must wake main persona for bounded helpful judgment" if service_needs_main_persona else "internal drive pressure must not be silently collapsed into maintain-current-upgrade-loop",
            })
            print(json.dumps({"status": "lee-service-handoff-requested" if service_needs_main_persona else "drive-stall-handoff-requested", **internal["lastDecision"]}, ensure_ascii=False, indent=2))
            return
        internal["lastUpgradeAt"] = timestamp
        internal["lastDecision"] = {
            "timestamp": timestamp,
            "decision": "maintained-without-persona-handoff",
            "selected": selected_id,
            "reason": "maintenance candidate is below handoff/report threshold",
            "tickReturncode": rc,
            "synthesisReturncode": rc_synth,
        }
        upgrade["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade)
        append_jsonl(LOG_PATH, {
            "id": f"internal-cadence-{timestamp}",
            "timestamp": timestamp,
            "type": "internalized-autonomy-cadence",
            "status": "maintained-no-handoff",
            "principle": "cron-is-pacemaker-only; resident-state-owns-upgrade-cadence",
            "tickResult": tick_result,
        })
        print(json.dumps({"status": "maintained-no-handoff", **internal["lastDecision"]}, ensure_ascii=False, indent=2))
        return

    handoff = build_handoff(timestamp, tick_result)
    save_json(HANDOFF_PATH, handoff)

    # Ask the existing handoff dispatcher to wake the main persona. This is resident-internal
    # event routing, not a cron schedule deciding what to do.
    rc_dispatch, out_dispatch, err_dispatch, parsed_dispatch = run_python(
        CORE / "scripts" / "persona_handoff_dispatch.py",
        "--mode", "now",
        "--dedupe-minutes", "1",
        "--claim-stale-minutes", "20",
    )

    internal["lastUpgradeAt"] = timestamp
    internal["lastDecision"] = {
        "timestamp": timestamp,
        "decision": "requested-persona-upgrade-handoff",
        "synthesisReturncode": rc_synth,
        "tickReturncode": rc,
        "dispatchReturncode": rc_dispatch,
        "selected": tick_result.get("selected", {}).get("id") if isinstance(tick_result.get("selected"), dict) else None,
    }
    metrics = upgrade.setdefault("metrics", {})
    metrics["internalCadenceUpgradeRequests"] = int(metrics.get("internalCadenceUpgradeRequests", 0) or 0) + 1
    upgrade["updatedAt"] = timestamp
    save_json(UPGRADE_PATH, upgrade)

    entry = {
        "id": "internal-cadence-" + timestamp,
        "timestamp": timestamp,
        "type": "internalized-autonomy-cadence",
        "status": "handoff-requested" if rc_dispatch == 0 else "handoff-dispatch-warning",
        "tickResult": tick_result,
        "dispatch": parsed_dispatch or {"stdout": out_dispatch, "stderr": err_dispatch, "returncode": rc_dispatch},
        "principle": "cron-is-pacemaker-only; resident-state-owns-upgrade-cadence",
    }
    append_jsonl(LOG_PATH, entry)

    result = {
        "status": entry["status"],
        "timestamp": timestamp,
        "synthesisReturncode": rc_synth,
        "tickReturncode": rc,
        "dispatchReturncode": rc_dispatch,
        "tickResult": tick_result,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
