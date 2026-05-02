from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(__import__("sys").stdout, "reconfigure"):
    __import__("sys").stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
UPGRADE_PATH = AUTO / "upgrade-state.json"
OUTPUT_PATH = STATE / "semantic_signal_layer.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def keywords(text: str) -> set[str]:
    text = text.lower()
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]{2,}|[\u4e00-\u9fff]{2,}", text)
    stop = {"the", "and", "that", "with", "for", "this", "into", "from", "state", "resident"}
    return {w for w in words if w not in stop}


def overlap_score(a: str, b: str) -> float:
    ka = keywords(a)
    kb = keywords(b)
    if not ka or not kb:
        return 0.0
    return round(len(ka & kb) / max(1, min(len(ka), len(kb))), 3)


def evidence_fingerprint(value: dict[str, Any]) -> str:
    """Stable, content-only fingerprint for repeatable evidence.

    Do not include timestamps: watchdog can refresh the same underlying
    low-value-loop evidence many times.  For repeatable verifier candidates we
    want completed-state suppression to apply to the same evidence, while a
    materially different watchdog observation can still become a new candidate.
    """
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:12]


def recent_actions(runtime: dict[str, Any]) -> list[str]:
    actions: list[str] = []
    for item in as_list(runtime.get("actions")):
        if not isinstance(item, dict) or item.get("action") != "resident-action":
            continue
        stdout = item.get("stdout")
        if not isinstance(stdout, str):
            continue
        try:
            parsed = json.loads(stdout)
        except Exception:
            continue
        selected = parsed.get("selectedAction") or parsed.get("review", {}).get("selectedAction")
        if selected:
            actions.append(str(selected))
    return actions


def build_layer() -> dict[str, Any]:
    timestamp = now_iso()
    upgrade = load_json(UPGRADE_PATH)
    perception = load_json(CORE / "perception-state.json")
    conversation = load_json(STATE / "conversation_insights.json")
    owner_chat = load_json(STATE / "owner_chat_signal_state.json")
    help_evidence = load_json(STATE / "lee_service_help_evidence.json")
    screen_semantic = load_json(STATE / "screen_semantic_summary.json")
    freshness_audit = load_json(STATE / "semantic_input_freshness_audit.json")
    opportunity = load_json(STATE / "lee_opportunity_review.json")
    watchdog = load_json(STATE / "autonomy_watchdog.json")
    world = load_json(CORE / "world-state.json")
    runtime = load_json(STATE / "resident_runtime.json")
    action_state = load_json(CORE / "action-state.json")
    goal_register = load_json(AUTO / "goal-register.json")
    completed_request_ids = {
        str(goal.get("id"))
        for goal in as_list(goal_register.get("candidates"))
        if isinstance(goal, dict) and goal.get("id") and goal.get("status") in {"completed", "done"}
    }
    for item in as_list(upgrade.get("completedConnectors")):
        if isinstance(item, dict) and item.get("id"):
            completed_request_ids.add(str(item.get("id")))
        elif item:
            completed_request_ids.add(str(item))
    for key in ("lastConnectorCompleted", "lastVerification"):
        item = upgrade.get(key)
        if isinstance(item, dict):
            for value_key in ("id", "selected"):
                if item.get(value_key):
                    completed_request_ids.add(str(item.get(value_key)))
    def completed_family_count(*prefixes: str) -> int:
        """Count unique completed connector evidence, not wrapper aliases.

        autonomy_upgrade_tick may record the same semantic request under base,
        advance-*, and advance-semantic-request-* ids.  Counting each alias as a
        separate completion prematurely saturates watchdog repair families and
        lets fresh low-value-loop evidence collapse back to maintenance.
        """
        canonical: set[str] = set()
        for completed_id in completed_request_ids:
            for prefix in prefixes:
                if completed_id.startswith(prefix):
                    canonical.add(completed_id[len(prefix) :])
                    break
        return len(canonical)

    completed_post_regression_verifier_count = completed_family_count(
        "watchdog-low-value-loop-post-regression-verifier-",
        "advance-watchdog-low-value-loop-post-regression-verifier-",
        "advance-semantic-request-watchdog-low-value-loop-post-regression-verifier-",
    )
    completed_semantic_post_regression_verifier_count = completed_family_count(
        "semantic-signal-candidate-generator-post-regression-verifier-",
        "advance-semantic-signal-candidate-generator-post-regression-verifier-",
        "advance-semantic-request-semantic-signal-candidate-generator-post-regression-verifier-",
    )
    completed_low_value_input_audit_count = completed_family_count(
        "watchdog-low-value-loop-input-source-audit-",
        "advance-watchdog-low-value-loop-input-source-audit-",
        "advance-semantic-request-watchdog-low-value-loop-input-source-audit-",
    )

    info = upgrade.get("informationScout", {}) if isinstance(upgrade.get("informationScout"), dict) else {}
    drive = info.get("homeostaticDrive") if isinstance(info.get("homeostaticDrive"), dict) else upgrade.get("homeostaticDrive", {})
    web = info.get("webScout", {}) if isinstance(info.get("webScout"), dict) else {}
    internal = upgrade.get("internalizedCadence", {}) if isinstance(upgrade.get("internalizedCadence"), dict) else {}
    last_decision = internal.get("lastDecision", {}) if isinstance(internal.get("lastDecision"), dict) else {}
    reach = opportunity.get("reachOutGate", {}) if isinstance(opportunity.get("reachOutGate"), dict) else {}
    decision = opportunity.get("decision", {}) if isinstance(opportunity.get("decision"), dict) else {}
    semantic = opportunity.get("semanticAssessment", {}) if isinstance(opportunity.get("semanticAssessment"), dict) else {}
    memory_loop = conversation.get("memoryControlLoop", {}) if isinstance(conversation.get("memoryControlLoop"), dict) else {}
    owner_bridge = conversation.get("ownerChatBridge", {}) if isinstance(conversation.get("ownerChatBridge"), dict) else {}
    predictions = world.get("predictions", []) if isinstance(world.get("predictions"), list) else []
    last_probe = as_list(perception.get("lastProbeSignals"))
    suppressed = as_list(perception.get("lastSuppressedSignals"))
    recent_exec = [x for x in as_list(action_state.get("recentExecutions")) if isinstance(x, dict)][-24:]

    observations: list[dict[str, Any]] = []
    candidate_requests: list[dict[str, Any]] = []

    def observe(**item: Any) -> None:
        observations.append(item)

    def request(**item: Any) -> None:
        item_id = str(item.get("id") or "")
        if item_id in completed_request_ids:
            return
        # Homeostatic wrapper connector ids are aliases for semantic request ids.
        # If either form has already been verified/completed, do not keep
        # emitting the same candidate request and creating false maintain-stall
        # handoffs.
        wrapper_id = "advance-homeostatic-drive-goal-" + item_id
        advance_id = "advance-" + item_id
        semantic_advance_id = "advance-semantic-request-" + item_id
        if wrapper_id in completed_request_ids or advance_id in completed_request_ids or semantic_advance_id in completed_request_ids:
            return
        candidate_requests.append(item)

    no_candidate_streak = safe_int(web.get("noCandidateStreak"), 0)
    drive_mode = str(drive.get("recommendedMode") or "maintain") if isinstance(drive, dict) else "maintain"
    scout_action = str(info.get("recommendedAction") or "hold")
    selected = str(last_decision.get("selected") or "")
    low_value_prediction = any(isinstance(p, dict) and p.get("id") == "low-value-maintenance-loop" for p in predictions)
    # If Lee-service drive is high only because a prepared-help packet was already
    # consumed and the action layer is deliberately holding quiet, do not count
    # that as a candidate-generation bottleneck.  It is a valid S1 quiet state
    # unless fresh external evidence or an explicit upgrade-now signal appears.
    consumed_guard_for_bottleneck = action_state.get("reachOutGateConsumedEvidenceGuard") if isinstance(action_state.get("reachOutGateConsumedEvidenceGuard"), dict) else {}
    guard_action_for_bottleneck = consumed_guard_for_bottleneck.get("actionSelectionGuard") if isinstance(consumed_guard_for_bottleneck.get("actionSelectionGuard"), dict) else {}
    opportunity_decision_for_bottleneck = opportunity.get("decision") if isinstance(opportunity.get("decision"), dict) else {}
    opportunity_value_signal_for_bottleneck = opportunity.get("valueSignal") if isinstance(opportunity.get("valueSignal"), dict) else {}
    opportunity_missing_for_bottleneck = as_list(opportunity_decision_for_bottleneck.get("missingEvidence")) + as_list(opportunity_decision_for_bottleneck.get("missingRequirements"))
    candidate_bottleneck_is_stale_service_drive = bool(
        drive_mode == "seek-helpful-contact"
        and consumed_guard_for_bottleneck.get("evidenceConsumed")
        and consumed_guard_for_bottleneck.get("helpEvidenceReady")
        and consumed_guard_for_bottleneck.get("lowersPrepareHelpPressure")
        and guard_action_for_bottleneck.get("mode") in {"prepared-but-quiet", "cooldown-suppressed-repeat"}
        and not (
            opportunity_value_signal_for_bottleneck.get("detected")
            and "external-signal" in as_list(opportunity_decision_for_bottleneck.get("evidence"))
            and "need-verification" not in opportunity_missing_for_bottleneck
        )
    )
    recent_confirmation_for_bottleneck = opportunity_decision_for_bottleneck.get("recentSimilarConfirmation") if isinstance(opportunity_decision_for_bottleneck.get("recentSimilarConfirmation"), dict) else {}
    candidate_bottleneck_is_recent_confirmed_screen_shift = bool(
        recent_confirmation_for_bottleneck.get("active")
        and "same-family-recently-confirmed" in as_list(opportunity_decision_for_bottleneck.get("suppressors"))
        and "need-verification" in opportunity_missing_for_bottleneck
        and opportunity_value_signal_for_bottleneck.get("suggestedNextLayer") == "S1-procedural"
    )
    candidate_bottleneck_fingerprint = evidence_fingerprint({
        "driveMode": drive_mode,
        "scoutAction": scout_action,
        "noCandidateStreak": no_candidate_streak,
        "lastSelected": selected,
        "lowValuePrediction": low_value_prediction,
    })
    watchdog_observations = [str(item) for item in as_list(watchdog.get("observations"))]
    watchdog_hint = str(watchdog.get("suggestedFix") or watchdog.get("loopAssessment") or "")
    substantive_watchdog_evidence = bool(watchdog_hint.strip()) or any(str(item).strip() for item in watchdog_observations)
    watchdog_evidence_fingerprint = evidence_fingerprint({
        "lowValueLoopHint": bool(watchdog.get("lowValueLoopHint")),
        "loopAssessment": watchdog.get("loopAssessment"),
        "suggestedFix": watchdog.get("suggestedFix"),
        "observations": watchdog_observations,
    })
    # The low-noise watchdog has had two schema generations: older runs wrote
    # free-form observations, while the current fallback writes a compact
    # lowValueLoopHint/suggestedFix pair.  Treat both as first-class semantic
    # evidence so a real maintain/continue-focus loop cannot disappear just
    # because the carrier schema changed.
    watchdog_low_value_loop = bool(watchdog.get("lowValueLoopHint")) or any(
        "low-value-loop" in item or "maintain/continue-focus" in item for item in watchdog_observations
    ) or "maintain/continue-focus" in watchdog_hint or "低价值" in watchdog_hint
    if watchdog_low_value_loop and selected in {"", "maintain-current-upgrade-loop"}:
        observe(
            id="watchdog-detected-maintenance-loop",
            severity="high",
            confidence=0.92,
            summary="Autonomy watchdog detected repeated maintain/continue-focus behavior without a fresh connector candidate.",
            evidence=[
                f"lastSelected={selected or 'unknown'}",
                f"lowValueLoopHint={bool(watchdog.get('lowValueLoopHint'))}",
                watchdog_hint[:240],
                *watchdog_observations[:3],
            ],
            suggestedConnector="autonomy_watchdog -> semanticSignalLayer -> candidateRequests -> autonomy_upgrade_tick",
        )
        request(
            id="watchdog-low-value-loop-breaker",
            title="watchdog 低价值维护循环断路器",
            gap="watchdog 已检测到 maintain/continue-focus 低价值循环，但该信号还没有稳定进入候选选择器。",
            nextConcreteStep="把 state/autonomy_watchdog.json 的低价值循环观察接入 semantic_signal_layer candidateRequests，并验证 autonomy_upgrade_tick dry-run 选择非 maintenance 候选。",
            sourceObservation="watchdog-detected-maintenance-loop",
            leeValue=1.0,
            feasibility=0.92,
            learningLeverage=0.98,
            noiseRisk=0.12,
        )
        if "watchdog-low-value-loop-breaker" in completed_request_ids and not candidate_requests:
            request(
                id="watchdog-low-value-loop-breaker-followup",
                title="watchdog 低价值维护循环断路器二阶修复",
                gap="watchdog 低价值循环断路器已完成，但新一轮 watchdog 仍检测到 maintain/continue-focus 压力没有形成新候选。",
                nextConcreteStep="让已完成的 watchdog breaker 进入后续验证：当 lowValueLoopHint 再次出现且 candidateRequests 为空时，生成二阶候选并验证 autonomy_upgrade_tick dry-run 不再退回纯 maintenance。",
                sourceObservation="watchdog-detected-maintenance-loop",
                leeValue=1.0,
                feasibility=0.9,
                learningLeverage=0.96,
                noiseRisk=0.13,
            )
        if (
            "watchdog-low-value-loop-breaker" in completed_request_ids
            and "watchdog-low-value-loop-breaker-followup" in completed_request_ids
            and not candidate_requests
        ):
            request(
                id="watchdog-low-value-loop-regression-audit",
                title="watchdog 低价值维护循环回归审计",
                gap="watchdog breaker 及二阶 follow-up 均已完成，但当前语义层仍观测到 maintain/continue-focus 压力且 candidateRequests 为空，说明完成证据可能过早压制了新的回归证据。",
                nextConcreteStep="把已完成 connector 的抑制逻辑与最新 watchdog lowValueLoopHint 分离：保留去重，同时允许新的回归证据生成一个独立、可验证的候选。",
                sourceObservation="watchdog-detected-maintenance-loop",
                leeValue=1.0,
                feasibility=0.88,
                learningLeverage=0.97,
                noiseRisk=0.14,
            )
        if (
            "watchdog-low-value-loop-breaker" in completed_request_ids
            and "watchdog-low-value-loop-breaker-followup" in completed_request_ids
            and "watchdog-low-value-loop-regression-audit" in completed_request_ids
            and completed_post_regression_verifier_count < 9
            and not candidate_requests
        ):
            # After one verified post-regression watchdog candidate, do not let
            # bare lowValueLoopHint=True (with no concrete suggestedFix or
            # observations) mint a fresh fingerprint every cadence tick. That
            # is ambient maintain-loop pressure, not materially new evidence.
            if completed_post_regression_verifier_count == 0 or substantive_watchdog_evidence:
                post_regression_id = "watchdog-low-value-loop-post-regression-verifier-" + watchdog_evidence_fingerprint
                request(
                    id=post_regression_id,
                    title="watchdog 低价值维护循环后回归验证器",
                    gap="watchdog breaker、follow-up、regression-audit 都已完成，但最新 watchdog lowValueLoopHint 仍显示 maintain/continue-focus 且候选为空，说明完成态需要一个新的实时验证候选而不是继续被去重压制。",
                    nextConcreteStep="用最新 state/autonomy_watchdog.json.lowValueLoopHint 生成一次独立验证候选；验证 autonomy_upgrade_tick dry-run 能看到该候选，若通过再把完成态去重规则限制为同一 evidence fingerprint。",
                    sourceObservation="watchdog-detected-maintenance-loop",
                    evidenceFingerprint=watchdog_evidence_fingerprint,
                    baseRequestId="watchdog-low-value-loop-post-regression-verifier",
                    leeValue=1.0,
                    feasibility=0.87,
                    learningLeverage=0.97,
                    noiseRisk=0.14,
                )
        if (
            "watchdog-low-value-loop-breaker" in completed_request_ids
            and "watchdog-low-value-loop-breaker-followup" in completed_request_ids
            and "watchdog-low-value-loop-regression-audit" in completed_request_ids
            and completed_post_regression_verifier_count >= 9
            and not candidate_requests
        ):
            request(
                id="watchdog-low-value-loop-saturation-cleanup-policy",
                title="watchdog 低价值循环饱和后的清理策略",
                gap="watchdog low-value-loop verifier 已多次完成，继续生成同族 verifier 只会制造完成态噪声；但当前仍有 maintain/continue-focus 压力，需要把下一步切到 evidence cleanup / owner-chat / screen semantic 路由，而不是继续同一类验证器。",
                nextConcreteStep="把 low-value-loop verifier 饱和状态写成清理策略：停止同族 verifier 扩增，优先检查 owner-chat freshness、screen semantic/OCR、reachOutGate evidence 三个真实输入源是否缺 writeback。",
                sourceObservation="watchdog-detected-maintenance-loop",
                evidenceFingerprint=watchdog_evidence_fingerprint,
                completedVerifierCount=completed_post_regression_verifier_count,
                leeValue=1.0,
                feasibility=0.89,
                learningLeverage=0.98,
                noiseRisk=0.1,
            )
        if (
            "watchdog-low-value-loop-saturation-cleanup-policy" in completed_request_ids
            and completed_low_value_input_audit_count < 3
            and substantive_watchdog_evidence
            and not candidate_requests
        ):
            request(
                id="watchdog-low-value-loop-input-source-audit-" + watchdog_evidence_fingerprint,
                title="watchdog 低价值循环输入源审计",
                gap="low-value-loop cleanup policy 已完成，但 watchdog 仍看到 maintain/continue-focus 压力；下一步应审计真实输入源 writeback，而不是继续生成同族 verifier。",
                nextConcreteStep="按 owner-chat freshness、screen semantic/OCR、reachOutGate evidence 三个输入源做一次只读审计，找出哪一路缺少可进入 action_ranker/autonomy_upgrade_tick 的新证据。",
                sourceObservation="watchdog-detected-maintenance-loop",
                evidenceFingerprint=watchdog_evidence_fingerprint,
                baseRequestId="watchdog-low-value-loop-input-source-audit",
                leeValue=1.0,
                feasibility=0.91,
                learningLeverage=0.98,
                noiseRisk=0.1,
            )
    if (
        (scout_action == "upgrade-now" or drive_mode not in {"maintain", "continue-focus"} or low_value_prediction)
        and selected in {"", "maintain-current-upgrade-loop"}
        and not (
            (candidate_bottleneck_is_stale_service_drive or candidate_bottleneck_is_recent_confirmed_screen_shift)
            and scout_action != "upgrade-now"
            and not low_value_prediction
        )
    ):
        confidence = 0.7 + min(0.25, no_candidate_streak * 0.04)
        observe(
            id="candidate-generation-bottleneck",
            severity="high" if no_candidate_streak >= 4 else "medium",
            confidence=round(confidence, 3),
            summary="Drive/scout pressure exists but upgrade selection still collapses to maintain-current-upgrade-loop.",
            evidence=[f"driveMode={drive_mode}", f"scoutAction={scout_action}", f"noCandidateStreak={no_candidate_streak}", f"lastSelected={selected}"],
            suggestedConnector="semanticSignalLayer -> goal-register -> autonomy_upgrade_tick concrete candidate requests",
        )
        request(
            id="semantic-signal-candidate-generator",
            title="语义信号到候选连接器生成器",
            gap="resident 能看到 drive/scout/Lee-service 压力，但缺少把复杂语义压力转成具体 connector 候选的中间层。",
            nextConcreteStep="把 state/semantic_signal_layer.json.candidateRequests 接入 autonomy_goal_synthesizer/autonomy_upgrade_tick，优先生成可验证的小连接器。",
            sourceObservation="candidate-generation-bottleneck",
            leeValue=1.0,
            feasibility=0.86,
            learningLeverage=1.0,
            noiseRisk=0.18,
        )
        if "semantic-signal-candidate-generator" in completed_request_ids and not candidate_requests:
            request(
                id="semantic-signal-candidate-generator-followup",
                title="语义候选生成器完成后仍维护空转的二阶修复",
                gap="语义候选生成器已标记完成，但 active observations 仍显示 candidate-generation-bottleneck，说明完成证据尚未让升级选择器产生新候选。",
                nextConcreteStep="把 state/semantic_signal_layer.json.candidateRequests 作为 autonomy_upgrade_tick 的一等候选源，并用 dry-run 验证非 maintenance 选择。",
                sourceObservation="candidate-generation-bottleneck",
                leeValue=1.0,
                feasibility=0.9,
                learningLeverage=1.0,
                noiseRisk=0.16,
            )
        if (
            "semantic-signal-candidate-generator" in completed_request_ids
            and any(
                completed in completed_request_ids
                for completed in (
                    "semantic-signal-candidate-generator-followup",
                    "advance-semantic-signal-candidate-generator-followup",
                    "advance-semantic-request-semantic-signal-candidate-generator-followup",
                )
            )
            and not candidate_requests
        ):
            request(
                id="semantic-signal-candidate-generator-regression-audit",
                title="语义候选生成器回归审计",
                gap="语义候选生成器及 follow-up 已完成，但 semantic_signal_layer 仍观测到 candidate-generation-bottleneck 且 candidateRequests 为空，说明完成态去重把新的回归证据也压掉了。",
                nextConcreteStep="把 candidate-generation-bottleneck 的最新证据与已完成 connector 去重分离；允许新的回归审计候选进入 autonomy_upgrade_tick dry-run，并验证 selector 不再只返回 maintenance。",
                sourceObservation="candidate-generation-bottleneck",
                leeValue=1.0,
                feasibility=0.88,
                learningLeverage=1.0,
                noiseRisk=0.15,
            )
        semantic_saturation_cleanup_done = any(
            completed in completed_request_ids
            for completed in (
                "semantic-signal-candidate-generator-saturation-cleanup-policy",
                "advance-semantic-signal-candidate-generator-saturation-cleanup-policy",
                "advance-semantic-request-semantic-signal-candidate-generator-saturation-cleanup-policy",
            )
        )
        if (
            "semantic-signal-candidate-generator" in completed_request_ids
            and any(
                completed in completed_request_ids
                for completed in (
                    "semantic-signal-candidate-generator-followup",
                    "advance-semantic-signal-candidate-generator-followup",
                    "advance-semantic-request-semantic-signal-candidate-generator-followup",
                )
            )
            and any(
                completed in completed_request_ids
                for completed in (
                    "semantic-signal-candidate-generator-regression-audit",
                    "advance-semantic-signal-candidate-generator-regression-audit",
                    "advance-semantic-request-semantic-signal-candidate-generator-regression-audit",
                )
            )
            and completed_semantic_post_regression_verifier_count < 9
            and not semantic_saturation_cleanup_done
            and not candidate_requests
        ):
            request(
                id="semantic-signal-candidate-generator-post-regression-verifier-" + candidate_bottleneck_fingerprint,
                title="语义候选生成器后回归验证器",
                gap="semantic generator、follow-up、regression-audit 都已完成，但最新 drive/scout 压力仍回落到 maintain 且候选为空，说明完成态需要按最新证据生成独立验证候选。",
                nextConcreteStep="用最新 candidate-generation-bottleneck evidence fingerprint 生成一次独立验证候选；验证 autonomy_upgrade_tick dry-run 能看到该候选，若通过再把完成态去重规则限制为同一 fingerprint。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                baseRequestId="semantic-signal-candidate-generator-post-regression-verifier",
                leeValue=1.0,
                feasibility=0.88,
                learningLeverage=1.0,
                noiseRisk=0.14,
            )
        if (
            "semantic-signal-candidate-generator" in completed_request_ids
            and any(
                completed in completed_request_ids
                for completed in (
                    "semantic-signal-candidate-generator-followup",
                    "advance-semantic-signal-candidate-generator-followup",
                    "advance-semantic-request-semantic-signal-candidate-generator-followup",
                )
            )
            and any(
                completed in completed_request_ids
                for completed in (
                    "semantic-signal-candidate-generator-regression-audit",
                    "advance-semantic-signal-candidate-generator-regression-audit",
                    "advance-semantic-request-semantic-signal-candidate-generator-regression-audit",
                )
            )
            and completed_semantic_post_regression_verifier_count >= 9
            and not semantic_saturation_cleanup_done
            and not candidate_requests
        ):
            request(
                id="semantic-signal-candidate-generator-saturation-cleanup-policy",
                title="语义候选生成器饱和后的清理策略",
                gap="semantic candidate generator verifier 已多次完成，继续生成同族 verifier 会制造完成态噪声；下一步应切到真实输入源清理策略。",
                nextConcreteStep="停止同族 semantic verifier 扩增，优先检查 owner-chat freshness、screen semantic/OCR、reachOutGate evidence 三个真实输入源是否缺 writeback。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                completedVerifierCount=completed_semantic_post_regression_verifier_count,
                leeValue=1.0,
                feasibility=0.89,
                learningLeverage=0.98,
                noiseRisk=0.1,
            )
        if semantic_saturation_cleanup_done and not candidate_requests:
            request(
                id="semantic-input-source-freshness-audit",
                title="语义输入源新鲜度审计",
                gap="semantic candidate generator 的同族验证器和饱和清理策略都已完成，但当前仍观测到 candidate-generation-bottleneck；下一步应审计真实输入源，而不是继续生成同族 verifier。",
                nextConcreteStep="对 owner-chat freshness、screen semantic/OCR、reachOutGate evidence 做一次只读新鲜度审计，并把缺失 writeback 的最小修复点交给 autonomy_upgrade_tick。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                completedVerifierCount=completed_semantic_post_regression_verifier_count,
                leeValue=1.0,
                feasibility=0.9,
                learningLeverage=0.98,
                noiseRisk=0.1,
            )
        freshness_audit_done = any(
            completed in completed_request_ids
            for completed in (
                "semantic-input-source-freshness-audit",
                "advance-semantic-input-source-freshness-audit",
                "advance-semantic-request-semantic-input-source-freshness-audit",
            )
        )
        screen_ocr_probe_done = any(
            completed in completed_request_ids
            for completed in (
                "screen-ocr-availability-probe",
                "advance-screen-ocr-availability-probe",
                "advance-semantic-request-screen-ocr-availability-probe",
            )
        )
        freshness_findings = [item for item in as_list(freshness_audit.get("findings")) if isinstance(item, dict)]
        bottleneck_without_request = any(item.get("id") == "candidate-bottleneck-without-request" for item in freshness_findings)
        freshness_inputs = freshness_audit.get("inputs", {}) if isinstance(freshness_audit.get("inputs"), dict) else {}
        screen_inputs = freshness_inputs.get("screenSemantic", {}) if isinstance(freshness_inputs.get("screenSemantic"), dict) else {}
        freshness_reach = freshness_inputs.get("reachOutGate", {}) if isinstance(freshness_inputs.get("reachOutGate"), dict) else {}
        decision = opportunity.get("decision", {}) if isinstance(opportunity.get("decision"), dict) else {}
        missing_evidence = set(as_list(decision.get("missingEvidence"))) | set(as_list(reach.get("missingEvidence"))) | set(as_list(freshness_reach.get("missingEvidence")))
        current_screen_hash = str(screen_semantic.get("screenHash") or "")
        audited_screen_hash = str(screen_inputs.get("screenHash") or screen_inputs.get("screenStateHash") or "")
        screen_hash_still_matches = bool(screen_inputs.get("hashMatch")) and bool(audited_screen_hash) and current_screen_hash == audited_screen_hash
        screen_verification_still_missing = "need-verification" in missing_evidence
        if freshness_audit_done and bottleneck_without_request and not candidate_requests:
            request(
                id="semantic-freshness-audit-continuation-guard",
                title="语义新鲜度审计后的候选延续守护",
                gap="freshness audit 已完成，但 semantic_signal_layer 仍观测到 candidate-generation-bottleneck 且 candidateRequests 为空；需要把审计发现转成下一步具体候选，而不是回到维护。",
                nextConcreteStep="根据 state/semantic_input_freshness_audit.json 的 findings 生成下一条最小修复候选；若 screen hash 匹配且仍缺验证，优先探测 OCR/更深屏幕语义是否可用。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                screenHashMatch=screen_hash_still_matches,
                screenVerificationStillMissing=screen_verification_still_missing,
                leeValue=1.0,
                feasibility=0.9,
                learningLeverage=0.98,
                noiseRisk=0.11,
            )
        if freshness_audit_done and bottleneck_without_request and screen_hash_still_matches and screen_verification_still_missing and not candidate_requests:
            request(
                id="screen-ocr-availability-probe",
                title="屏幕 OCR/深层语义可用性探测",
                gap="当前 screen_semantic_summary 只有 active-window 与截图元数据；freshness audit 后仍有 need-verification/candidate bottleneck，下一步应先低成本探测本机是否有 OCR 或更深 UI 语义能力，而不是直接引入重模型。",
                nextConcreteStep="只读检查本机 OCR/Windows.Media.Ocr/tesseract/Python OCR 依赖是否可用；若不可用，记录原因并保持 active-window 轻量路径，不占用显存。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                leeValue=0.96,
                feasibility=0.86,
                learningLeverage=0.95,
                noiseRisk=0.08,
            )
        if freshness_audit_done and bottleneck_without_request and screen_ocr_probe_done and screen_verification_still_missing and not candidate_requests:
            request(
                id="screen-semantic-ocr-writeback-audit",
                title="屏幕 OCR/语义写回路径审计",
                gap="screen OCR availability probe 已完成，但 reachOutGate/opportunity 仍缺 need-verification；低价值循环需要确认 OCR/active-window 证据是否真正写回 semantic/opportunity evidence。",
                nextConcreteStep="只读检查 state/screen_semantic_summary.json、state/lee_opportunity_review.json、state/semantic_input_freshness_audit.json，确认 screen semantic/OCR 证据是否进入 reachOutGate missingEvidence；若缺口存在，生成最小 writeback connector。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                screenVerificationStillMissing=screen_verification_still_missing,
                leeValue=0.98,
                feasibility=0.88,
                learningLeverage=0.96,
                noiseRisk=0.09,
            )
        if freshness_audit_done and bottleneck_without_request and screen_ocr_probe_done and screen_hash_still_matches and screen_verification_still_missing and not candidate_requests:
            visual_writeback_fingerprint = evidence_fingerprint({
                "base": "reachout-visual-verification-writeback",
                "screenHash": current_screen_hash,
                "auditedScreenHash": audited_screen_hash,
                "missingEvidence": sorted(str(item) for item in missing_evidence),
            })
            request(
                id="reachout-visual-verification-writeback-" + visual_writeback_fingerprint,
                title="reachOutGate visual verification writeback",
                gap="screen semantic/OCR audit is complete and current screen hash still matches the freshness audit, but reachOutGate still reports need-verification; write a small auditable visual-verification evidence marker instead of returning to maintenance.",
                nextConcreteStep="Read current screen_semantic_summary and lee_opportunity_review; if the screen hash still matches and only need-verification is missing, write a screenVerificationEvidence/visualEvidenceConsumed marker and verify autonomy_upgrade_tick dry-run selects a non-maintenance connector.",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=visual_writeback_fingerprint,
                baseRequestId="reachout-visual-verification-writeback",
                screenHashMatch=screen_hash_still_matches,
                screenVerificationStillMissing=screen_verification_still_missing,
                leeValue=0.98,
                feasibility=0.9,
                learningLeverage=0.96,
                noiseRisk=0.08,
            )

        if bottleneck_without_request and not candidate_requests:
            freshness_fingerprint = evidence_fingerprint({
                "findingIds": [str(item.get("id")) for item in freshness_findings],
                "nextPatch": freshness_audit.get("nextPatch"),
                "screenHashMatch": screen_hash_still_matches,
                "missingEvidence": sorted(str(item) for item in missing_evidence),
            })
            resolved_bottleneck_fingerprints = {
                str(item.get("evidenceFingerprint"))
                for item in as_list(freshness_audit.get("resolvedFindings"))
                if isinstance(item, dict)
                and item.get("id") == "candidate-bottleneck-without-request"
                and item.get("evidenceFingerprint")
            }
            saturation_done = any(
                completed in completed_request_ids
                for completed in (
                    "semantic-input-bottleneck-fingerprint-saturation-cleanup",
                    "advance-semantic-input-bottleneck-fingerprint-saturation-cleanup",
                    "advance-semantic-request-semantic-input-bottleneck-fingerprint-saturation-cleanup",
                )
            )
            if len(resolved_bottleneck_fingerprints) >= 2:
                if not saturation_done:
                    request(
                        id="semantic-input-bottleneck-fingerprint-saturation-cleanup",
                        title="语义输入瓶颈 fingerprint 饱和清理",
                        gap="semantic_input_freshness_audit 的同族 candidate-bottleneck-without-request 已产生多个 fingerprint；继续逐个完成 current-finding 只会制造 verifier 噪声。",
                        nextConcreteStep="把同族 fingerprint 饱和写成稳定策略：记录已消费 fingerprints，停止同族 current-finding 扩增，只有新鲜具体输入源证据才重新开放候选。",
                        sourceObservation="candidate-generation-bottleneck",
                        evidenceFingerprint=freshness_fingerprint,
                        previousResolvedFingerprints=sorted(resolved_bottleneck_fingerprints),
                        baseRequestId="semantic-input-bottleneck-fingerprint-saturation-cleanup",
                        leeValue=1.0,
                        feasibility=0.91,
                        learningLeverage=0.99,
                        noiseRisk=0.08,
                    )
            elif not saturation_done and freshness_fingerprint not in resolved_bottleneck_fingerprints:
                request(
                    id="semantic-input-bottleneck-current-finding-" + freshness_fingerprint,
                    title="语义输入瓶颈当前发现转候选",
                    gap="semantic_input_freshness_audit 已确认 candidate-generation-bottleneck-without-request，但既有完成态去重让 semantic_signal_layer.candidateRequests 为空。",
                    nextConcreteStep="把当前 freshness audit finding 作为带 fingerprint 的一次性候选交给 autonomy_upgrade_tick；验证 dry-run 不再只选择 maintain-current-upgrade-loop。",
                    sourceObservation="candidate-generation-bottleneck",
                    evidenceFingerprint=freshness_fingerprint,
                    baseRequestId="semantic-input-bottleneck-current-finding",
                    leeValue=1.0,
                    feasibility=0.9,
                    learningLeverage=0.98,
                    noiseRisk=0.1,
                )
            elif saturation_done and not candidate_requests:
                routing_audit_done = any(
                    completed == "semantic-input-bottleneck-saturation-routing-audit"
                    or completed == "advance-semantic-input-bottleneck-saturation-routing-audit"
                    or completed == "advance-semantic-request-semantic-input-bottleneck-saturation-routing-audit"
                    or completed.startswith("semantic-input-bottleneck-saturation-routing-audit-")
                    or completed.startswith("advance-semantic-input-bottleneck-saturation-routing-audit-")
                    or completed.startswith("advance-semantic-request-semantic-input-bottleneck-saturation-routing-audit-")
                    for completed in completed_request_ids
                )
                # Emit the saturation routing audit once. If a concrete input gap
                # remains after that audit, let the more specific downstream branches
                # (screen OCR / reachOutGate / owner-chat) produce the next candidate
                # instead of re-issuing this same routing-audit family with a new fingerprint.
                if not routing_audit_done:
                    request(
                        id="semantic-input-bottleneck-saturation-routing-audit-" + freshness_fingerprint,
                        title="语义输入瓶颈饱和后的路由审计",
                        gap="semantic_input_bottleneck current-finding 家族已完成饱和清理，但当前新鲜度审计仍观测到 candidate-generation-bottleneck；继续发 current-finding 会被 autonomy_upgrade_tick 正确过滤并回到 maintain。",
                        nextConcreteStep="停止生成已饱和的 current-finding 候选，审计 freshness_audit -> semantic_signal_layer -> autonomy_upgrade_tick 的饱和后路由，确认下一步应转向 owner-chat、screen semantic/OCR 或 reachOutGate evidence 的具体输入源写回。",
                        sourceObservation="candidate-generation-bottleneck",
                        evidenceFingerprint=freshness_fingerprint,
                        baseRequestId="semantic-input-bottleneck-saturation-routing-audit",
                        leeValue=0.98,
                        feasibility=0.92,
                        learningLeverage=0.97,
                        noiseRisk=0.08,
                    )
        if not candidate_requests and "homeostatic-drive-stalled-on-maintain-router-repair" not in completed_request_ids:
            request(
                id="homeostatic-drive-stalled-on-maintain-router-repair-" + candidate_bottleneck_fingerprint,
                title="驱动压力到候选路由断点修复",
                gap="homeostaticDrive / informationScout 已明确要求 upgrade-now，但同族 semantic verifier 与 input-bottleneck 路由候选已进入完成或饱和抑制，导致 autonomy_upgrade_tick 只能回到 maintain-current-upgrade-loop。",
                nextConcreteStep="把本次 drive/scout/top-goal 压力作为一次性 router-repair 候选交给 autonomy_upgrade_tick；验证选择器能选中非维护项，完成后只抑制同一 evidence fingerprint，未来只在新具体输入源证据出现时重开。",
                sourceObservation="candidate-generation-bottleneck",
                evidenceFingerprint=candidate_bottleneck_fingerprint,
                baseRequestId="homeostatic-drive-stalled-on-maintain-router-repair",
                leeValue=1.0,
                feasibility=0.91,
                learningLeverage=0.98,
                noiseRisk=0.09,
            )

    limitation = str(conversation.get("limitation") or "")
    if "live chat" in limitation.lower() or "实时" in limitation:
        owner_chat_ready = bool(owner_chat.get("lastSignalId"))
        owner_chat_stale_minutes = None
        try:
            last_ingested = datetime.fromisoformat(str(owner_chat.get("lastIngestedAt")).replace("Z", "+00:00"))
            owner_chat_stale_minutes = (datetime.now(last_ingested.tzinfo or timezone.utc) - last_ingested).total_seconds() / 60.0
        except Exception:
            owner_chat_stale_minutes = None
        owner_chat_bridge_completed = any(
            item in completed_request_ids
            for item in (
                "owner-chat-runtime-auto-hook-freshness-bridge",
                "advance-owner-chat-runtime-auto-hook-freshness-bridge",
                "advance-semantic-request-owner-chat-runtime-auto-hook-freshness-bridge",
            )
        )
        owner_chat_accounted = owner_chat_ready and owner_chat_bridge_completed and owner_chat_stale_minutes is not None and not bool(owner_bridge.get("staleDespiteInbox"))
        owner_chat_fresh = owner_chat_accounted and owner_chat_stale_minutes < 45
        observe(
            id="live-chat-ingestion-gap",
            severity="low" if owner_chat_accounted else ("medium" if owner_chat_ready else "high"),
            confidence=0.55 if owner_chat_accounted else (0.7 if owner_chat_ready else 0.92),
            summary=(
                "Owner-chat ingestion freshness bridge is verified and fresh; remaining live-chat limitation is being monitored rather than treated as an upgrade gap."
                if owner_chat_fresh
                else (
                    "Owner-chat ingestion bridge is verified; marker is aged but no newer bounded owner-chat intent is waiting, so this is monitoring evidence rather than a fresh upgrade gap."
                    if owner_chat_accounted
                    else ("Resident conversation memory still depends on bounded inbox writes; owner-chat ingestion endpoint exists but runtime auto-hook is not yet first-class." if owner_chat_ready else "Resident conversation memory still depends on memory/inbox writes; live owner chat is not a first-class signal.")
                )
            ),
            evidence=[limitation[:240], f"ownerChatEndpointReady={owner_chat_ready}", f"lastOwnerChatSignal={owner_chat.get('lastSignalId')}", f"ownerChatBridgeCompleted={owner_chat_bridge_completed}", f"ownerChatStaleMinutes={round(owner_chat_stale_minutes, 1) if owner_chat_stale_minutes is not None else 'unknown'}"],
            suggestedConnector="monitor owner-chat freshness; generate candidate only if staleDespiteInbox or endpoint missing" if owner_chat_accounted else "owner-chat -> conversation_insight_inbox -> conversation_insight_tick -> semanticSignalLayer",
        )
        if not owner_chat_ready:
            request(
                id="safe-owner-chat-signal-ingestion",
                title="安全 owner-chat 信号摄取",
                gap="Lee 的实时意图不能稳定进入 resident 语义层，导致复杂信息处理滞后。",
                nextConcreteStep="建立只接收 owner-chat 摘要/意图的 append-only inbox 写入规范，并让 semantic_signal_layer 标记新鲜 Lee 指令。",
                sourceObservation="live-chat-ingestion-gap",
                leeValue=1.0,
                feasibility=0.78,
                learningLeverage=0.94,
                noiseRisk=0.22,
            )
        elif owner_chat_stale_minutes is None or owner_chat_stale_minutes >= 45:
            stale_despite_inbox = bool(owner_bridge.get("staleDespiteInbox"))
            bridge_missing = not bool(owner_bridge)
            if stale_despite_inbox or bridge_missing:
                observe(
                    id="owner-chat-endpoint-stale-despite-live-intent",
                    severity="high",
                    confidence=0.84,
                    summary="owner-chat signal endpoint is configured, but the freshness marker is stale while conversation insight still records newer Lee/watchdog autonomy intent.",
                    evidence=[
                        f"ownerChatStaleMinutes={round(owner_chat_stale_minutes, 1) if owner_chat_stale_minutes is not None else 'unknown'}",
                        f"lastOwnerChatSignal={owner_chat.get('lastSignalId')}",
                        f"latestInboxOwnerSignalAt={owner_bridge.get('latestInboxOwnerSignalAt')}",
                        f"conversationInsightsAt={conversation.get('timestamp')}",
                    ],
                    suggestedConnector="owner_chat_signal_state freshness -> conversation_insight_tick -> semanticSignalLayer candidateRequests",
                )
                request(
                    id="owner-chat-runtime-auto-hook-freshness-bridge",
                    title="owner-chat runtime auto-hook freshness bridge",
                    gap="owner-chat endpoint exists, but its last ingested signal can go stale while new Lee/watchdog intent only reaches bounded inbox/memory, so resident still treats live chat as a limitation.",
                    nextConcreteStep="wire owner_chat_signal_state freshness into conversation_insight_tick/semantic_signal_layer so fresh owner intent refreshes the resident route without manual memory flushes.",
                    sourceObservation="live-chat-ingestion-gap",
                    leeValue=1.0,
                    feasibility=0.82,
                    learningLeverage=0.96,
                    noiseRisk=0.18,
                )
            else:
                observe(
                    id="owner-chat-endpoint-aged-without-newer-owner-intent",
                    severity="low",
                    confidence=0.72,
                    summary="owner-chat signal marker is old, but conversation_insight_tick confirms there is no newer bounded owner-chat signal waiting to refresh it.",
                    evidence=[
                        f"ownerChatStaleMinutes={round(owner_chat_stale_minutes, 1) if owner_chat_stale_minutes is not None else 'unknown'}",
                        f"lastOwnerChatSignal={owner_chat.get('lastSignalId')}",
                        f"latestInboxOwnerSignalAt={owner_bridge.get('latestInboxOwnerSignalAt')}",
                        f"ownerBridgeRefreshed={owner_bridge.get('refreshedOwnerState')}",
                    ],
                    suggestedConnector="no candidate; wait for fresh owner-chat inbox signal",
                )

        # Fresh explicit owner instructions should not be reduced to mere
        # freshness monitoring.  If Lee has just asked for autonomy/interface
        # upgrade and the selector has no stronger concrete candidate, emit a
        # bounded per-signal request so the instruction enters goal-register /
        # autonomy_upgrade_tick as an actionable connector candidate.
        owner_intents = [str(x) for x in as_list(owner_chat.get("lastIntents"))]
        signal_id = str(owner_chat.get("lastSignalId") or "owner-chat")
        safe_signal_id = re.sub(r"[^a-zA-Z0-9_-]+", "-", signal_id)[-48:]
        if owner_chat_ready and owner_chat_stale_minutes is not None and owner_chat_stale_minutes < 45 and "autonomy-upgrade" in owner_intents:
            observe(
                id="fresh-owner-autonomy-upgrade-instruction",
                severity="medium",
                confidence=0.88,
                summary="Lee issued a fresh autonomy-upgrade instruction; resident should turn it into one concrete local connector rather than only marking chat freshness.",
                evidence=[
                    f"lastOwnerChatSignal={signal_id}",
                    f"ownerChatStaleMinutes={round(owner_chat_stale_minutes, 1)}",
                    f"lastOwnerChatIntents={owner_intents}",
                    f"scoutAction={scout_action}",
                    f"driveMode={drive_mode}",
                ],
                suggestedConnector="fresh owner-chat instruction -> semanticSignalLayer candidateRequests -> goal-register/autonomy_upgrade_tick",
            )
            request(
                id="owner-instruction-active-upgrade-router-" + safe_signal_id,
                title="fresh owner instruction active upgrade router",
                gap="Lee 刚明确要求继续升级本地持续接口，但当前 selector 仍可能退回 maintain；需要把这条 owner-chat 信号转成一个可验证的本地连接器候选。",
                nextConcreteStep="选择并执行一个安全、可逆、可验证的本地持续接口升级点；验证后把结果写回 self/continuity/memory，而不是只刷新 owner-chat timestamp。",
                sourceObservation="fresh-owner-autonomy-upgrade-instruction",
                leeValue=1.0,
                feasibility=0.9,
                learningLeverage=0.98,
                noiseRisk=0.12,
            )

    if reach.get("leeServiceDrive") is not None:
        service_drive = safe_float(reach.get("leeServiceDrive"), 0.0)
        missing = as_list(reach.get("missingEvidence")) + as_list(reach.get("mustRequirements"))
        reach_decision = str(reach.get("decision") or "")
        if service_drive >= 0.9 and reach_decision in {"prepare-help-silently", "prepare-help-silently-with-evidence"}:
            help_packet_ok = help_evidence.get("verification", {}).get("status") == "ok"
            evidence_consumed = reach_decision == "prepare-help-silently-with-evidence" or bool(
                reach.get("helpEvidence", {}).get("consumed") if isinstance(reach.get("helpEvidence"), dict) else False
            )
            consumed_guard = action_state.get("reachOutGateConsumedEvidenceGuard") if isinstance(action_state.get("reachOutGateConsumedEvidenceGuard"), dict) else {}
            guard_action = consumed_guard.get("actionSelectionGuard") if isinstance(consumed_guard.get("actionSelectionGuard"), dict) else {}
            guard_active = bool(
                consumed_guard.get("evidenceConsumed")
                and consumed_guard.get("helpEvidenceReady")
                and consumed_guard.get("lowersPrepareHelpPressure")
                and guard_action.get("mode") in {"prepared-but-quiet", "cooldown-suppressed-repeat"}
            )
            decision_evidence = as_list(decision.get("evidence")) if isinstance(decision, dict) else []
            value_signal = opportunity.get("valueSignal") if isinstance(opportunity.get("valueSignal"), dict) else {}
            has_fresh_external_evidence = bool(
                value_signal.get("detected")
                and "external-signal" in decision_evidence
                and "need-verification" not in missing
            )
            guard_suppresses_stale_pressure = bool(guard_active and not has_fresh_external_evidence)
            observe(
                id="lee-service-drive-evidence-gap",
                severity="low" if help_packet_ok else "medium",
                confidence=0.5 if guard_suppresses_stale_pressure else (0.62 if help_packet_ok else 0.86),
                summary=(
                    "Lee-service evidence packet is consumed and the action-selection guard now treats the remaining high service-drive as prepared-but-quiet unless fresh external evidence appears."
                    if guard_suppresses_stale_pressure
                    else ("Lee-service evidence packet has been consumed by reachOutGate; remaining work is verifying that consumed evidence writes back into service-drive/action selection instead of leaving a perpetual prepare-help loop." if evidence_consumed and help_packet_ok else ("Lee-service evidence packet exists; remaining work is making reachOutGate consume it directly." if help_packet_ok else "Lee-service drive is high, but reachOutGate lacks semantic evidence to decide useful contact/help."))
                ),
                evidence=[
                    f"leeServiceDrive={service_drive}",
                    f"reachDecision={reach_decision}",
                    f"missing={missing[:4]}",
                    f"helpEvidenceReady={help_packet_ok}",
                    f"helpEvidenceConsumed={evidence_consumed}",
                    f"helpEvidenceMode={help_evidence.get('recommendation', {}).get('mode')}",
                    f"semanticAttention={semantic.get('recommendedAttention')}",
                    f"consumedGuardActive={guard_active}",
                    f"hasFreshExternalEvidence={has_fresh_external_evidence}",
                ],
                suggestedConnector="reachOutGate consumed evidence -> service-drive writeback/action selection guard",
            )
            if evidence_consumed and help_packet_ok and not guard_suppresses_stale_pressure and not candidate_requests:
                request(
                    id="reachoutgate-consumed-evidence-writeback-audit",
                    title="reachOutGate 已消费帮助证据后的写回审计",
                    gap="reachOutGate 已消费 verified helpEvidence，但 leeServiceDrive 仍保持高位且升级选择器回到 maintain；需要确认“已准备帮助/仍不打扰”的证据会写回 drive/action 层，避免继续被误判成候选生成瓶颈。",
                    nextConcreteStep="只读审计 state/lee_opportunity_review.json、state/lee_service_help_evidence.json、core/world-state.json 与 autonomy_upgrade_tick 选择结果；若 consumed evidence 没有降低 prepare-help 压力或生成 action-selection guard，补一条本地状态写回。",
                    sourceObservation="lee-service-drive-evidence-gap",
                    leeValue=0.96,
                    feasibility=0.9,
                    learningLeverage=0.94,
                    noiseRisk=0.1,
                )
                # If the base audit has already been verified but the same
                # high service-drive / prepare-help loop remains, do not let
                # completion de-duplication collapse back to maintenance.
                # Emit one concrete follow-up candidate that targets the
                # post-audit writeback/action-selection guard directly.
                reachoutgate_audit_done = any(
                    completed in completed_request_ids
                    for completed in (
                        "reachoutgate-consumed-evidence-writeback-audit",
                        "advance-reachoutgate-consumed-evidence-writeback-audit",
                        "advance-semantic-request-reachoutgate-consumed-evidence-writeback-audit",
                        "advance-homeostatic-drive-goal-reachoutgate-consumed-evidence-writeback-audit",
                    )
                )
                if reachoutgate_audit_done and not candidate_requests:
                    request(
                        id="reachoutgate-consumed-evidence-action-selection-guard",
                        title="reachOutGate consumed evidence action-selection guard",
                        gap="The reachOutGate consumed-evidence audit is completed, but leeServiceDrive remains high and the selector still falls back to maintain; the consumed evidence needs an explicit action-selection suppression/writeback guard.",
                        nextConcreteStep="Write a local, reversible guard that records consumed helpEvidence as lowering prepare-help pressure unless new external evidence appears, then verify autonomy_upgrade_tick dry-run no longer selects only maintenance for the same stale evidence.",
                        sourceObservation="lee-service-drive-evidence-gap",
                        leeValue=0.96,
                        feasibility=0.88,
                        learningLeverage=0.95,
                        noiseRisk=0.1,
                    )
            elif not help_packet_ok:
                request(
                    id="lee-service-evidence-builder",
                    title="Lee-service 证据构建器",
                    gap="想帮 Lee 的驱动强，但缺少把最近信号/记忆/目标综合成具体帮助建议的证据包。",
                    nextConcreteStep="生成一个 helpEvidence packet：recent Lee intent + current focus + blockers + candidate useful action，并交给 handoff/报告门判断。",
                    sourceObservation="lee-service-drive-evidence-gap",
                    leeValue=0.98,
                    feasibility=0.82,
                    learningLeverage=0.9,
                    noiseRisk=0.2,
                )

    screen_signals = [s for s in last_probe + suppressed if isinstance(s, dict) and s.get("type") == "screen-changed"]
    recent_semantic_writes = sum(1 for e in recent_exec if isinstance(e.get("semanticWriteback"), dict) and e.get("semanticWriteback", {}).get("applied"))
    current_screen_hash = perception.get("lastScreenHash")
    screen_summary_current = bool(screen_semantic.get("screenHash") and screen_semantic.get("screenHash") == current_screen_hash)
    if screen_signals and recent_semantic_writes == 0:
        observe(
            id="screen-hash-without-semantics",
            severity="low" if screen_summary_current else "medium",
            confidence=0.58 if screen_summary_current else 0.78,
            summary="Screen semantic summary exists for the current hash; remaining work is deeper OCR/visual interpretation." if screen_summary_current else "Screen changes are mostly hash-level evidence; resident lacks OCR/UI semantic summaries before deciding S1/S2.",
            evidence=[f"screenSignals={len(screen_signals)}", f"recentSemanticWritebacks={recent_semantic_writes}", f"screenSummaryCurrent={screen_summary_current}", f"screenLabels={screen_semantic.get('classification', {}).get('labels')}"],
            suggestedConnector="screen-state -> OCR/UI summary -> opportunity_semantic_assessor",
        )
        if not screen_summary_current:
            request(
                id="screen-change-semantic-summarizer",
                title="屏幕变化语义摘要器",
                gap="screen-changed 现在主要是 hash 变化，难以识别 Lee 是否卡住、完成任务或出现机会。",
                nextConcreteStep="为 screen_state 增加轻量 active-window/OCR/视觉摘要入口，先只写 state，不直接行动。",
                sourceObservation="screen-hash-without-semantics",
                leeValue=0.9,
                feasibility=0.72,
                learningLeverage=0.88,
                noiseRisk=0.16,
            )

    if memory_loop:
        read_hook = json.dumps(memory_loop.get("read", {}), ensure_ascii=False)
        action_text = json.dumps(world.get("actionCandidates", [])[:4], ensure_ascii=False)
        overlap = overlap_score(read_hook, action_text)
        if overlap < 0.12:
            observe(
                id="memory-read-not-driving-actions",
                severity="medium",
                confidence=0.74,
                summary="memoryControlLoop exists, but its read hooks are not strongly reflected in current world action candidates.",
                evidence=[f"readActionOverlap={overlap}", "memoryControlLoop present"],
                suggestedConnector="memoryControlLoop.read -> world_model_tick/actionCandidates -> autonomy_upgrade_tick",
            )
            request(
                id="memory-read-action-coupler",
                title="记忆读回到行动候选耦合器",
                gap="conversation memory 已结构化，但读回结果还没有稳定影响 world-model/action candidate。",
                nextConcreteStep="让 world_model_tick 读取 memoryControlLoop/recentInsights，并在 actionCandidates 中生成 memory-backed candidate。",
                sourceObservation="memory-read-not-driving-actions",
                leeValue=0.94,
                feasibility=0.84,
                learningLeverage=0.96,
                noiseRisk=0.14,
            )

    active_goals = [g for g in as_list(goal_register.get("candidates")) if isinstance(g, dict) and g.get("status") in {"active", "queued"}]
    if len(active_goals) > 12 and no_candidate_streak >= 4:
        observe(
            id="goal-pool-high-but-selector-starved",
            severity="medium",
            confidence=0.8,
            summary="Goal register has many active goals, but selector still reports no useful connector; goal scoring/alias suppression is too coarse.",
            evidence=[f"activeGoals={len(active_goals)}", f"noCandidateStreak={no_candidate_streak}"],
            suggestedConnector="goal-register -> semanticSignalLayer candidate priority -> autonomy_upgrade_tick",
        )

    resource_pressure = freshness_audit.get("resourcePressure", {}) if isinstance(freshness_audit.get("resourcePressure"), dict) else {}
    resource_level = str(resource_pressure.get("level") or "")
    if resource_level in {"warning", "high", "critical"} and not candidate_requests:
        resource_fingerprint = evidence_fingerprint({
            "level": resource_level,
            "recommendedMode": resource_pressure.get("recommendedMode"),
            "reason": resource_pressure.get("reason"),
            "memory": resource_pressure.get("components", {}).get("memory") if isinstance(resource_pressure.get("components"), dict) else None,
        })
        observe(
            id="resource-pressure-needs-safe-mode-writeback",
            severity="high" if resource_level in {"high", "critical"} else "medium",
            confidence=0.86,
            summary="Resource pressure is present while semantic candidate generation is otherwise saturated; route next work toward cleanup/safe-mode writeback instead of heavier probes.",
            evidence=[
                f"resourceLevel={resource_level}",
                f"reason={resource_pressure.get('reason')}",
                f"recommendedMode={resource_pressure.get('recommendedMode')}",
            ],
            suggestedConnector="semantic_input_freshness_audit.resourcePressure -> autonomy_upgrade_tick safe-mode/cleanup candidate",
        )
        request(
            id="resource-pressure-safe-mode-writeback-" + resource_fingerprint,
            title="资源压力安全模式写回",
            gap="semantic_input_freshness_audit 已检测到本机资源压力，但候选生成饱和时容易继续空转或选择重探测。",
            nextConcreteStep="把当前 resourcePressure 写回 autonomy/continuity 状态和候选选择器：在内存 warning/high 时优先小型本地 CPU/清理/审计任务，避免 GPU 或重型 OCR/模型探测。",
            sourceObservation="resource-pressure-needs-safe-mode-writeback",
            evidenceFingerprint=resource_fingerprint,
            baseRequestId="resource-pressure-safe-mode-writeback",
            leeValue=0.92,
            feasibility=0.94,
            learningLeverage=0.86,
            noiseRisk=0.06,
        )

    severity_weight = {"high": 1.0, "medium": 0.55, "low": 0.25}
    semantic_pressure = round(min(1.0, sum(severity_weight.get(str(o.get("severity")), 0.2) * safe_float(o.get("confidence"), 0.5) for o in observations) / 2.2), 3)
    candidate_requests = sorted(candidate_requests, key=lambda r: (safe_float(r.get("leeValue"), 0), safe_float(r.get("learningLeverage"), 0), -safe_float(r.get("noiseRisk"), 0)), reverse=True)

    return {
        "timestamp": timestamp,
        "status": "ok",
        "purpose": "Compress complex resident inputs into explainable semantic observations and concrete candidate requests before any neural/ranker layer is trained.",
        "semanticPressure": semantic_pressure,
        "recommendedAction": "generate-candidates" if candidate_requests and semantic_pressure >= 0.55 else ("watch" if observations else "hold"),
        "observations": observations,
        "candidateRequests": candidate_requests[:8],
        "inputs": {
            "driveMode": drive_mode,
            "scoutAction": scout_action,
            "noCandidateStreak": no_candidate_streak,
            "lastCadenceSelected": selected,
            "lastProbeSignalCount": len(last_probe),
            "suppressedSignalCount": len(suppressed),
            "recentActionTail": recent_actions(runtime)[-5:],
            "memoryControlLoopPresent": bool(memory_loop),
        },
        "policy": {
            "explainableBeforeNeural": True,
            "advisoryOnly": True,
            "noExternalWrites": True,
            "candidateRequestsMustEnterGoalRegister": True,
        },
    }


def apply_layer(layer: dict[str, Any]) -> None:
    save_json(OUTPUT_PATH, layer)
    upgrade = load_json(UPGRADE_PATH)
    upgrade["semanticSignalLayer"] = {
        "enabled": True,
        "script": "core/scripts/semantic_signal_layer.py",
        "statePath": "state/semantic_signal_layer.json",
        "lastRunAt": layer.get("timestamp"),
        "semanticPressure": layer.get("semanticPressure"),
        "recommendedAction": layer.get("recommendedAction"),
        "candidateRequestIds": [item.get("id") for item in as_list(layer.get("candidateRequests")) if isinstance(item, dict)],
        "principle": "rules safety shell + explainable semantic compression now; embeddings/neural ranker can be added after enough labeled outcomes",
    }
    if layer.get("recommendedAction") == "generate-candidates":
        internal = upgrade.setdefault("internalizedCadence", {})
        internal["forceUpgradeRequestedAt"] = layer.get("timestamp")
        internal["forceUpgradeReason"] = "semantic-signal-layer:candidate-requests"
    upgrade["updatedAt"] = layer.get("timestamp") or now_iso()
    save_json(UPGRADE_PATH, upgrade)
    append_jsonl(LOG_PATH, {
        "id": "semantic-signal-layer-" + str(layer.get("timestamp")),
        "timestamp": layer.get("timestamp"),
        "type": "semantic-signal-layer",
        "status": layer.get("recommendedAction"),
        "semanticPressure": layer.get("semanticPressure"),
        "observationIds": [item.get("id") for item in as_list(layer.get("observations")) if isinstance(item, dict)],
        "candidateRequestIds": [item.get("id") for item in as_list(layer.get("candidateRequests")) if isinstance(item, dict)],
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    layer = build_layer()
    if not args.dry_run:
        apply_layer(layer)
    print(json.dumps({"ok": True, "dryRun": bool(args.dry_run), "semanticSignalLayer": layer}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
