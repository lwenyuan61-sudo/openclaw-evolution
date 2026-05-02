from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
LOG_PATH = AUTO / "experiment-log.jsonl"
UPGRADE_PATH = AUTO / "upgrade-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


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


def contains_ability(registry: dict[str, Any], ability_id: str) -> bool:
    return any(item.get("id") == ability_id for item in registry.get("abilities", []) if isinstance(item, dict))


def contains_action(registry: dict[str, Any], action_id: str) -> bool:
    return action_id in (registry.get("residentActions", {}) or {})


def recent_log_count(path: Path, limit: int = 20) -> int:
    if not path.exists():
        return 0
    try:
        lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return 0
    return len(lines[-limit:])


def build_candidates(context: dict[str, Any]) -> list[dict[str, Any]]:
    self_state = context["self_state"]
    goal_register = context["goal_register"]
    learning_state = context["learning_state"]
    procedural_memory = context.get("procedural_memory", {})
    deliberation_state = context.get("deliberation_state", {})
    capability_registry = context["capability_registry"]
    upgrade_state = context["upgrade_state"]
    persona_handoff = context.get("persona_handoff", {}) if isinstance(context.get("persona_handoff"), dict) else {}
    semantic_layer = context.get("semantic_layer", {}) if isinstance(context.get("semantic_layer"), dict) else {}

    open_loops = "\n".join(str(x) for x in self_state.get("openLoops", []) if x)
    candidate_ids = {c.get("id") for c in goal_register.get("candidates", []) if isinstance(c, dict)}
    counters = learning_state.get("counters", {}) if isinstance(learning_state.get("counters"), dict) else {}
    verified_episodes = int(counters.get("deliberationEpisodesVerified", 0) or 0)
    compiled_patterns = int(counters.get("deliberationPatternsCompiled", 0) or 0)
    # Some S1 compilations cover an entire repeated S2 family, not just one
    # pattern row. Track covered episode count separately so the resident does
    # not keep selecting the same compile-more connector after a family has
    # already been compressed.
    covered_by_s1 = int(counters.get("deliberationEpisodesCoveredByS1", 0) or 0)
    # Derive family-level S1 coverage from procedural memory too. The counter
    # can lag behind resident-written deliberation patterns; episodeIds on S1
    # patterns/habits are the more direct proof that a whole repeated family is
    # already compressed into cheap handling.
    s1_episode_ids: set[str] = set()
    has_screen_s1_family = False
    s1_family_stat_coverage = 0
    for pattern in procedural_memory.get("deliberationPatterns", []) or []:
        if not isinstance(pattern, dict) or pattern.get("preferredLayer") != "S1-procedural":
            continue
        conditions = pattern.get("conditions", {}) if isinstance(pattern.get("conditions"), dict) else {}
        if "screen-changed" in set(conditions.get("signalTypesAnyOf", []) or []) and "real-desktop-change" in set(conditions.get("signalProvenanceAnyOf", []) or []):
            has_screen_s1_family = True
            stats = pattern.get("stats", {}) if isinstance(pattern.get("stats"), dict) else {}
            s1_family_stat_coverage = max(s1_family_stat_coverage, int(stats.get("verified", 0) or 0), int(stats.get("success", 0) or 0))
        for episode_id in pattern.get("episodeIds", []) or []:
            if episode_id:
                s1_episode_ids.add(str(episode_id))
    for habit in procedural_memory.get("habits", []) or []:
        if not isinstance(habit, dict) or habit.get("preferredAction") != "silent-wait":
            continue
        conditions = habit.get("conditions", {}) if isinstance(habit.get("conditions"), dict) else {}
        if "screen-changed" in set(conditions.get("signalTypesAnyOf", []) or []) and "real-desktop-change" in set(conditions.get("signalProvenanceAnyOf", []) or []):
            has_screen_s1_family = True
            stats = habit.get("stats", {}) if isinstance(habit.get("stats"), dict) else {}
            s1_family_stat_coverage = max(s1_family_stat_coverage, int(stats.get("verified", 0) or 0), int(stats.get("success", 0) or 0))
        for episode_id in habit.get("episodeIds", []) or []:
            if episode_id:
                s1_episode_ids.add(str(episode_id))
    if has_screen_s1_family:
        for episode in deliberation_state.get("recentEpisodes", []) or []:
            if not isinstance(episode, dict):
                continue
            if episode.get("compiledPatternId") == "deliberation-screen-changed-real-desktop-change" and episode.get("trigger") == "compiled-from-repeated-verified-s2-same-family-cooldown" and episode.get("episodeId"):
                s1_episode_ids.add(str(episode.get("episodeId")))
    covered_by_s1 = max(covered_by_s1, len(s1_episode_ids), s1_family_stat_coverage)
    s2_compile_debt = max(0, verified_episodes - max(compiled_patterns, covered_by_s1))

    completed_connector_ids = {
        str(item.get("id"))
        for item in [upgrade_state.get("lastConnectorCompleted")]
        if isinstance(item, dict) and item.get("id")
    }
    completed_connector_ids.update(
        str(item.get("selected"))
        for item in [upgrade_state.get("lastVerification")]
        if isinstance(item, dict) and item.get("status") == "ok" and item.get("selected")
    )
    # Keep durable suppression history, not just the last completed connector.
    # Otherwise a new verified connector overwrites lastConnectorCompleted and an
    # older completed direct candidate (for example extend-non-screen-signal-triage)
    # can be selected again on the next dry-run.
    for item in upgrade_state.get("completedConnectors", []) or []:
        if isinstance(item, dict) and item.get("id"):
            completed_connector_ids.add(str(item.get("id")))
        elif item:
            completed_connector_ids.add(str(item))

    candidates: list[dict[str, Any]] = []

    def add(**item: Any) -> None:
        item_id = str(item.get("id"))
        if item_id in completed_connector_ids:
            return
        semantic_bottleneck_saturation_done = any(
            completed in completed_connector_ids
            for completed in (
                "semantic-input-bottleneck-fingerprint-saturation-cleanup",
                "advance-semantic-input-bottleneck-fingerprint-saturation-cleanup",
                "advance-semantic-request-semantic-input-bottleneck-fingerprint-saturation-cleanup",
                "advance-homeostatic-drive-goal-semantic-input-bottleneck-fingerprint-saturation-cleanup",
            )
        )
        semantic_bottleneck_routing_audit_done = any(
            completed == "semantic-input-bottleneck-saturation-routing-audit"
            or completed == "advance-semantic-input-bottleneck-saturation-routing-audit"
            or completed == "advance-semantic-request-semantic-input-bottleneck-saturation-routing-audit"
            or completed.startswith("semantic-input-bottleneck-saturation-routing-audit-")
            or completed.startswith("advance-semantic-input-bottleneck-saturation-routing-audit-")
            or completed.startswith("advance-semantic-request-semantic-input-bottleneck-saturation-routing-audit-")
            for completed in completed_connector_ids
        )
        if semantic_bottleneck_saturation_done and (
            item_id.startswith("advance-semantic-input-bottleneck-current-finding-")
            or item_id.startswith("advance-homeostatic-drive-goal-semantic-input-bottleneck-current-finding-")
        ):
            return
        if semantic_bottleneck_routing_audit_done and (
            item_id.startswith("advance-semantic-input-bottleneck-saturation-routing-audit-")
            or item_id.startswith("advance-homeostatic-drive-goal-semantic-input-bottleneck-saturation-routing-audit-")
        ):
            return
        # Goal-backed drive wrappers are aliases for the underlying goal
        # connector. If the direct web-scout/goal connector is already durably
        # completed, do not reselect it through the homeostatic wrapper on the
        # next cadence tick.
        prefix = "advance-homeostatic-drive-goal-"
        if item_id.startswith(prefix):
            goal_suffix = item_id.removeprefix(prefix)
            if goal_suffix in completed_connector_ids or ("advance-" + goal_suffix) in completed_connector_ids:
                return
        semantic_prefix = "advance-semantic-request-"
        if item_id.startswith(semantic_prefix):
            request_suffix = item_id.removeprefix(semantic_prefix)
            if (
                request_suffix in completed_connector_ids
                or ("advance-" + request_suffix) in completed_connector_ids
                or ("advance-homeostatic-drive-goal-" + request_suffix) in completed_connector_ids
            ):
                return
            # After the semantic-input-bottleneck current-finding family has
            # reached fingerprint saturation, stale persona-handoff snapshots
            # must not re-open another one-off verifier just because they
            # preserve an already-dispatched semantic request.  Re-open this
            # family only when semantic_signal_layer emits a fresh concrete
            # input-source candidate, not from preserved current-finding ids.
            if request_suffix.startswith("semantic-input-bottleneck-current-finding-") and semantic_bottleneck_saturation_done:
                return
            if request_suffix.startswith("semantic-input-bottleneck-saturation-routing-audit-") and semantic_bottleneck_routing_audit_done:
                return
        candidates.append(item)

    information_scout = upgrade_state.get("informationScout", {}) if isinstance(upgrade_state.get("informationScout"), dict) else {}
    scout_semantic_layer = information_scout.get("semanticSignalLayer", {}) if isinstance(information_scout.get("semanticSignalLayer"), dict) else {}
    handoff_tick = persona_handoff.get("autonomyTickResult", {}) if isinstance(persona_handoff.get("autonomyTickResult"), dict) else {}
    handoff_scout = handoff_tick.get("informationScout", {}) if isinstance(handoff_tick.get("informationScout"), dict) else {}
    handoff_semantic_layer = handoff_scout.get("semanticSignalLayer", {}) if isinstance(handoff_scout.get("semanticSignalLayer"), dict) else {}
    scout_drive = information_scout.get("homeostaticDrive", {}) if isinstance(information_scout.get("homeostaticDrive"), dict) else {}
    stored_drive = upgrade_state.get("homeostaticDrive", {}) if isinstance(upgrade_state.get("homeostaticDrive"), dict) else {}
    # The info scout writes the freshest drive vector under informationScout.
    # The older top-level homeostaticDrive field can be stale; using only that
    # field collapses a real upgrade-now drive back into maintain-current.
    homeostatic_drive = scout_drive or stored_drive
    drive_mode = homeostatic_drive.get("recommendedMode")
    scout_findings = information_scout.get("findings", []) if isinstance(information_scout.get("findings"), list) else []
    scout_recommends_upgrade = information_scout.get("recommendedAction") == "upgrade-now" or any(
        isinstance(finding, dict) and finding.get("severity") == "high" for finding in scout_findings
    )
    # The scout can recommend upgrade-now from multiple medium pressures
    # (for example leeServiceDrive + fresh local signal) even when the drive's
    # own mode is seek-helpful-contact. Treat that as internal upgrade pressure
    # for candidate generation, not as permission to contact Lee directly.
    drive_requests_upgrade = drive_mode in {"upgrade-now", "compile-learning", "read-only-scout", "seek-helpful-contact"} or scout_recommends_upgrade
    if drive_requests_upgrade:
        add(
            id="repair-homeostatic-drive-candidate-routing",
            title="修复内稳态驱动到候选生成的路由断点",
            gap="informationScout 已经给出最新 recommendedAction/drive pressure，但候选选择器若只看少数 drive modes 或只生成已完成连接器，就会退回 maintain-current。",
            connector="informationScout.homeostaticDrive -> autonomy_upgrade_tick.build_candidates -> goal-backed connector",
            usesExistingPieces=[
                "homeostatic_drive_arbiter.py",
                "autonomy_info_scout.py",
                "autonomy_upgrade_tick.py",
                "experiment-log.jsonl",
            ],
            minimalAction="让 build_candidates 优先使用 informationScout.homeostaticDrive / recommendedAction，并在 scout 高压时把 topGoalIds 转成现有 goal-register 支撑的真实候选。",
            verification=[
                "homeostatic_drive_arbiter.py --dry-run bounded drives",
                "autonomy_info_scout.py includes homeostaticDrive finding",
                "autonomy_upgrade_tick.py --dry-run selects a non-maintenance connector when drive pressure is high",
                "consistency_check.py",
                "module_linkage_audit.py",
            ],
            leeValue=0.98,
            feasibility=0.9,
            learningLeverage=0.98,
            noiseRisk=0.16,
            finalFormPressure=True,
            homeostaticArousal=float(homeostatic_drive.get("arousal", 0.0) or 0.0),
        )

    for finding in scout_findings:
        if not isinstance(finding, dict):
            continue
        finding_id = str(finding.get("id") or "")
        if finding_id == "resident-runtime-action-failure":
            failed_actions = finding.get("failedActions", []) if isinstance(finding.get("failedActions"), list) else []
            failed_name = "unknown-action"
            if failed_actions and isinstance(failed_actions[0], dict) and failed_actions[0].get("action"):
                failed_name = str(failed_actions[0].get("action"))
            add(
                id="repair-resident-runtime-action-failure-" + failed_name.replace("_", "-").replace(" ", "-"),
                title="修复 resident runtime 失败动作：" + failed_name,
                gap=str(finding.get("summary") or "resident runtime 报告了失败动作，但升级选择器没有把它变成可执行 repair candidate。"),
                connector="resident_runtime.failedActions -> autonomy_info_scout.findings -> autonomy_upgrade_tick repair candidate",
                usesExistingPieces=["state/resident_runtime.json", "autonomy_info_scout.py", "autonomy_upgrade_tick.py", "experiment-log.jsonl"],
                minimalAction="检查失败动作的 stderr / 状态文件；若当前失败已恢复，则记录路由修复并防止同类 high finding 只触发 maintain。",
                verification=["autonomy_info_scout.py reports runtime failure finding", "autonomy_upgrade_tick.py --dry-run selects runtime failure repair candidate", "failed script/state validates or stale failure is suppressed", "consistency_check.py"],
                leeValue=0.98,
                feasibility=0.88,
                learningLeverage=0.96,
                noiseRisk=0.14,
                finalFormPressure=True,
            )
        elif finding_id == "consistency-drift":
            add(
                id="repair-consistency-drift-from-information-scout",
                title="修复 information scout 发现的一致性漂移",
                gap=str(finding.get("summary") or "consistency_check warning/error should become an autonomy repair candidate."),
                connector="consistency_report -> autonomy_info_scout.findings -> autonomy_upgrade_tick repair candidate",
                usesExistingPieces=["state/consistency_report.json", "autonomy_info_scout.py", "autonomy_upgrade_tick.py"],
                minimalAction="读取 consistency_report 并执行最小状态修复，然后跑 consistency_check.py。",
                verification=["consistency_check.py returns ok", "autonomy_upgrade_tick.py --dry-run no longer selects the drift repair"],
                leeValue=0.94,
                feasibility=0.9,
                learningLeverage=0.9,
                noiseRisk=0.12,
                finalFormPressure=True,
            )

    # SemanticSignalLayer is the low-cost bridge from observations like
    # candidate-generation-bottleneck into concrete, scoreable upgrade work.
    # Use the latest state file, the scout snapshot stored in upgrade-state,
    # and the active persona-handoff snapshot. Resident ticks can refresh
    # state/semantic_signal_layer.json or upgrade-state between handoff dispatch
    # and main-persona claim; the handoff snapshot preserves the request that
    # caused the handoff so it is still a first-class candidate source instead
    # of collapsing back to maintenance.
    semantic_requests: list[dict[str, Any]] = []
    seen_semantic_request_ids: set[str] = set()
    for layer in (semantic_layer, scout_semantic_layer, handoff_semantic_layer):
        for request in layer.get("candidateRequests", []) or []:
            if not isinstance(request, dict) or not request.get("id"):
                continue
            request_id = str(request.get("id"))
            if request_id in seen_semantic_request_ids:
                continue
            seen_semantic_request_ids.add(request_id)
            semantic_requests.append(request)

    for request in semantic_requests:
        add(
            id="advance-semantic-request-" + str(request.get("id")),
            title="推进语义候选请求：" + str(request.get("title") or request.get("id")),
            gap=str(request.get("gap") or "semantic_signal_layer 产生了需要进入升级选择器的候选请求。"),
            connector="semantic_signal_layer.candidateRequests -> autonomy_upgrade_tick -> verification/log/writeback",
            usesExistingPieces=["semantic_signal_layer.py", "state/semantic_signal_layer.json", "autonomy_upgrade_tick.py", "experiment-log.jsonl"],
            minimalAction=str(request.get("nextConcreteStep") or "把语义候选请求转成一个可验证的最小连接器。"),
            verification=["semantic_signal_layer.py --dry-run emits candidateRequests", "autonomy_upgrade_tick.py --dry-run selects non-maintenance when semantic requests exist", "consistency_check.py"],
            leeValue=float(request.get("leeValue", 0.92) or 0.92),
            feasibility=float(request.get("feasibility", 0.8) or 0.8),
            learningLeverage=float(request.get("learningLeverage", 0.9) or 0.9),
            noiseRisk=float(request.get("noiseRisk", 0.2) or 0.2),
            finalFormPressure=True,
            sourceObservation=request.get("sourceObservation"),
        )

    # A main-persona handoff can be triggered by a dry-run selected semantic
    # candidate even when the resident refreshes semantic_signal_layer.json
    # before the owner persona claims the handoff.  Preserve that selected
    # object as a candidate source too, otherwise a real, already-dispatched
    # regression audit can collapse back to maintain-current-upgrade-loop just
    # because the live advisory layer is now quieter.
    handoff_selected = handoff_tick.get("selected") if isinstance(handoff_tick.get("selected"), dict) else {}
    handoff_selected_id = str(handoff_selected.get("id") or "")
    if handoff_selected_id.startswith("advance-semantic-request-"):
        add(
            id=handoff_selected_id,
            title=str(handoff_selected.get("title") or "推进语义候选请求"),
            gap=str(handoff_selected.get("gap") or "persona handoff preserved a semantic request selected by the resident dry-run."),
            connector=str(handoff_selected.get("connector") or "persona_handoff.autonomyTickResult.selected -> autonomy_upgrade_tick"),
            usesExistingPieces=handoff_selected.get("usesExistingPieces") if isinstance(handoff_selected.get("usesExistingPieces"), list) else ["persona_deliberation_handoff.json", "autonomy_upgrade_tick.py"],
            minimalAction=str(handoff_selected.get("minimalAction") or "执行 handoff 中已选中的语义候选并写回验证结果。"),
            verification=handoff_selected.get("verification") if isinstance(handoff_selected.get("verification"), list) else ["autonomy_upgrade_tick.py --dry-run selects the preserved handoff candidate", "consistency_check.py"],
            leeValue=float(handoff_selected.get("leeValue", 0.92) or 0.92),
            feasibility=float(handoff_selected.get("feasibility", 0.8) or 0.8),
            learningLeverage=float(handoff_selected.get("learningLeverage", 0.9) or 0.9),
            noiseRisk=float(handoff_selected.get("noiseRisk", 0.2) or 0.2),
            finalFormPressure=True,
            sourceObservation=handoff_selected.get("sourceObservation") or "persona-handoff-selected-semantic-request",
        )

    if drive_requests_upgrade:
        top_goal_ids = []
        evidence = homeostatic_drive.get("evidence", {}) if isinstance(homeostatic_drive.get("evidence"), dict) else {}
        for goal_id in evidence.get("topGoalIds", []) or []:
            if goal_id and goal_id not in top_goal_ids:
                top_goal_ids.append(str(goal_id))
        goals_by_id = {
            str(goal.get("id")): goal
            for goal in goal_register.get("candidates", []) or []
            if isinstance(goal, dict) and goal.get("id") and goal.get("status") in {"active", "queued"}
        }
        # Do not stop at the first few pressure goals: durable suppression can
        # remove already-completed high-priority connectors, and then a hard
        # drive vector must be allowed to fall through to the next active
        # goal-backed connector instead of collapsing back to maintenance.
        for goal_id in top_goal_ids:
            goal = goals_by_id.get(goal_id)
            if not goal:
                continue
            add(
                id="advance-homeostatic-drive-goal-" + goal_id,
                title="响应内稳态驱动推进目标：" + str(goal.get("title") or goal_id),
                gap=str(goal.get("subgoal") or goal.get("goal") or "高压内稳态驱动需要落到现有目标池中的真实下一步。"),
                connector="informationScout.homeostaticDrive -> goal-register -> autonomy_upgrade_tick -> verification/log/writeback",
                usesExistingPieces=["autonomy_info_scout.py", "homeostatic_drive_arbiter.py", "goal-register.json", "autonomy_upgrade_tick.py", "experiment-log.jsonl"],
                minimalAction=str(goal.get("nextConcreteStep") or "为该目标执行一个可验证的最小连接器。"),
                verification=["autonomy_upgrade_tick.py --dry-run selects non-maintenance under drive pressure", "consistency_check.py", "module_linkage_audit.py", "experiment-log entry"],
                leeValue=float(goal.get("leeValue", 0.92) or 0.92),
                feasibility=float(goal.get("feasibility", 0.82) or 0.82),
                learningLeverage=float(goal.get("learningLeverage", 0.9) or 0.9),
                noiseRisk=float(goal.get("noiseRisk", 0.2) or 0.2),
                finalFormPressure=True,
                homeostaticArousal=float(homeostatic_drive.get("arousal", 0.0) or 0.0),
            )

    if not contains_ability(capability_registry, "autonomy-self-upgrade") or not contains_action(capability_registry, "run-autonomy-upgrade-tick"):
        add(
            id="register-self-upgrade-connector",
            title="把自升级器注册进能力表与 resident action",
            gap="自升级闭环存在状态文件/脚本，但还没成为能力注册表中的一等公民。",
            connector="capability-registry -> resident action -> agency loop",
            usesExistingPieces=["capability-registry.json", "residentActions", "agency-loop"],
            minimalAction="注册 autonomy-self-upgrade 能力和 run-autonomy-upgrade-tick 动作。",
            verification=["consistency_check.py", "autonomy_upgrade_tick.py --dry-run"],
            leeValue=0.95,
            feasibility=0.96,
            learningLeverage=0.94,
            noiseRisk=0.12,
        )

    if "autonomy-self-upgrade-manager" not in candidate_ids:
        add(
            id="add-self-upgrade-track",
            title="把自升级管理器加入目标池",
            gap="自主性升级还没有作为可被 initiative review 选择的轨道。",
            connector="goal-register -> initiative-review -> self-state/continuity-state",
            usesExistingPieces=["goal-register.json", "initiative_review.py", "state_sync.py"],
            minimalAction="新增 autonomy-self-upgrade-manager 候选轨道。",
            verification=["initiative_review.py", "state_sync.py"],
            leeValue=0.98,
            feasibility=0.95,
            learningLeverage=0.98,
            noiseRisk=0.16,
        )

    if recent_log_count(LOG_PATH) == 0 or int(upgrade_state.get("metrics", {}).get("ticks", 0) or 0) == 0:
        add(
            id="start-experiment-log-loop",
            title="启动自升级实验日志",
            gap="自升级还缺少实验级证据链，容易只留下口头结论。",
            connector="autonomy_upgrade_tick -> experiment-log -> learning-state/continuity-state",
            usesExistingPieces=["upgrade-state.json", "learning-state.json", "continuity-state.json"],
            minimalAction="记录第一条 integration-only 自升级实验。",
            verification=["experiment-log has append-only entry", "upgrade-state metrics increment"],
            leeValue=0.9,
            feasibility=1.0,
            learningLeverage=0.9,
            noiseRisk=0.08,
        )

    if "非屏幕" in open_loops or "workspace" in open_loops or "provenance" in open_loops:
        add(
            id="extend-non-screen-signal-triage",
            title="把非屏幕信号接入同一套机会判断链",
            gap="screen-changed 已较成熟，workspace/artifact/device 等信号还没有同等强的语义机会闭环。",
            connector="signal-probe -> opportunity_semantic_assessor -> persona_handoff_dispatch -> resident_reflection",
            usesExistingPieces=["signal_probe.py", "opportunity_semantic_assessor.py", "persona_handoff_dispatch.py", "resident_reflection.py"],
            minimalAction="生成下一步集成计划：优先 artifact 身份证据 path/hash，而非新增大模块。",
            verification=["dry-run candidate only", "future focused patch"],
            leeValue=0.96,
            feasibility=0.82,
            learningLeverage=1.0,
            noiseRisk=0.22,
        )

    if s2_compile_debt >= 3:
        add(
            id="compile-more-s2-into-s1",
            title="把更多已验证 S2 模式回落成 S1 习惯",
            gap="S2 已验证次数明显多于已编译模式，说明深推理结果还可继续压缩。",
            connector="deliberation-state -> learning_update -> procedural-memory",
            usesExistingPieces=["deliberation-state.json", "learning_update.py", "procedural-memory.json"],
            minimalAction="选择最近重复成功模式，准备编译成低成本习惯。",
            verification=["procedural-memory confidence/stats", "consistency_check.py"],
            leeValue=0.88,
            feasibility=0.86,
            learningLeverage=0.92,
            noiseRisk=0.14,
            s2CompileDebt=s2_compile_debt,
            finalFormPressure=s2_compile_debt >= 3,
        )

    # Creative/self-synthesized goal-register items can become concrete upgrade
    # candidates, but they still route through the same scoring, logging, and
    # verification loop. This keeps creativity connected instead of悬空.
    for goal in goal_register.get("candidates", []) or []:
        if not isinstance(goal, dict):
            continue
        source = str(goal.get("source", ""))
        if goal.get("status") not in {"active", "queued"}:
            continue
        if not (source.startswith("self-synthesized") or goal.get("id") in {"resident-internal-cadence-evolution", "module-linkage-auditor", "s2-to-s1-compiler-pressure"}):
            continue
        candidate: dict[str, Any] = dict(
            id="advance-" + str(goal.get("id")),
            title="推进整改目标：" + str(goal.get("title") or goal.get("id")),
            gap=str(goal.get("subgoal") or goal.get("goal") or "自生成整改目标需要进入执行闭环。"),
            connector="goal-register -> autonomy_upgrade_tick -> verification/log/writeback",
            usesExistingPieces=["goal-register.json", "autonomy_upgrade_tick.py", "experiment-log.jsonl", "consistency_check.py"],
            minimalAction=str(goal.get("nextConcreteStep") or "为该自生成目标执行一个最小连接器。"),
            verification=["py_compile-if-needed", "consistency_check.py", "experiment-log entry"],
            leeValue=float(goal.get("leeValue", 0.9) or 0.9),
            feasibility=float(goal.get("feasibility", 0.8) or 0.8),
            learningLeverage=float(goal.get("learningLeverage", 0.9) or 0.9),
            noiseRisk=float(goal.get("noiseRisk", 0.2) or 0.2),
            finalFormPressure=True,
        )
        if goal.get("id") == "s2-to-s1-compiler-pressure":
            candidate["s2CompileDebt"] = s2_compile_debt
            candidate["verifiedEpisodes"] = verified_episodes
            candidate["compiledPatterns"] = compiled_patterns
            candidate["minimalAction"] = (
                "把 verified-minus-compiled="
                f"{s2_compile_debt} 写入候选评分压力，优先释放 S2 到 S1 编译债。"
            )
            candidate["verification"] = [
                "autonomy_upgrade_tick.py --dry-run shows s2CompileDebt pressure",
                "py_compile-if-needed",
                "consistency_check.py",
                "experiment-log entry",
            ]
        add(**candidate)

    if not candidates:
        add(
            id="maintain-current-upgrade-loop",
            title="维持当前自升级闭环并等待更清晰缺口",
            gap="没有发现比当前主线更高价值的低风险连接缺口。",
            connector="upgrade-state -> continuity-state",
            usesExistingPieces=["upgrade-state.json", "continuity-state.json"],
            minimalAction="只做一次低成本 tick 和连续性回写。",
            verification=["upgrade-state metrics increment"],
            leeValue=0.65,
            feasibility=1.0,
            learningLeverage=0.55,
            noiseRisk=0.03,
        )

    return candidates


def score_candidate(item: dict[str, Any], resource_pressure: dict[str, Any] | None = None) -> float:
    # Value is primary: Lee's final-form target outweighs merely being low risk.
    # Risk still subtracts, but it is a boundary/recovery signal, not the main objective.
    score = 0.0
    score += float(item.get("leeValue", 0.0)) * 4.2
    score += float(item.get("learningLeverage", 0.0)) * 2.8
    score += float(item.get("feasibility", 0.0)) * 1.5
    score -= float(item.get("noiseRisk", 0.0)) * 1.0
    if item.get("finalFormPressure"):
        score += 0.8
    homeostatic_arousal = float(item.get("homeostaticArousal", 0.0) or 0.0)
    if homeostatic_arousal > 0:
        score += min(0.9, homeostatic_arousal * 0.9)
    # Verified S2 outcomes that are not yet compiled into S1 habits are a
    # concrete autonomy debt: they keep future wakes expensive. Let that debt
    # apply pressure to upgrade selection without bypassing normal scoring.
    s2_compile_debt = int(item.get("s2CompileDebt", 0) or 0)
    if s2_compile_debt > 0:
        score += min(1.2, s2_compile_debt * 0.12)
    if "->" in str(item.get("connector", "")):
        score += 0.35
    if len(item.get("usesExistingPieces", []) or []) >= 3:
        score += 0.25

    pressure = resource_pressure or {}
    pressure_level = str(pressure.get("level") or "").lower()
    recommended_mode = str(pressure.get("recommendedMode") or "").lower()
    if pressure_level in {"warning", "high", "critical"} or "avoid-heavy" in recommended_mode:
        text = " ".join(
            str(item.get(key, ""))
            for key in ("id", "title", "gap", "connector", "minimalAction")
        ).lower()
        heavy_terms = ("gpu", "ocr", "model", "vision", "deep-screen", "heavy", "browser", "web-scout")
        if any(term in text for term in heavy_terms) and "resource-pressure-safe-mode" not in text:
            score -= 1.2
            item["resourcePressurePenalty"] = True
        safe_terms = ("cpu", "cleanup", "audit", "safe-mode", "resource-pressure", "maintain-current")
        if any(term in text for term in safe_terms):
            score += 0.35
            item["resourcePressurePreferred"] = True
        item["resourcePressureMode"] = pressure.get("recommendedMode") or pressure_level
    return round(score, 3)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one integration-only autonomy self-upgrade tick.")
    parser.add_argument("--dry-run", action="store_true", help="compute candidate and report without writing")
    args = parser.parse_args()

    timestamp = now_iso()
    default_upgrade = {
        "enabled": True,
        "purpose": "把自主性升级从一次性人工设计，变成由现有回路组合出的可验证闭环。",
        "principle": "integration-over-creation",
        "loop": [
            "scan-existing-state",
            "detect-autonomy-gap",
            "select-smallest-connector",
            "run-or-stage-low-risk-change",
            "verify-with-existing-gates",
            "log-experiment",
            "write-back-continuity",
        ],
        "currentExperiment": None,
        "lastResult": None,
        "blockers": [],
        "metrics": {},
        "connectionPolicy": {},
    }

    context = {
        "self_state": load_json(CORE / "self-state.json"),
        "continuity": load_json(AUTO / "continuity-state.json"),
        "goal_register": load_json(AUTO / "goal-register.json"),
        "learning_state": load_json(CORE / "learning-state.json"),
        "procedural_memory": load_json(CORE / "procedural-memory.json"),
        "deliberation_state": load_json(CORE / "deliberation-state.json"),
        "capability_registry": load_json(CORE / "capability-registry.json"),
        "upgrade_state": load_json(UPGRADE_PATH, default_upgrade),
        "semantic_layer": load_json(STATE / "semantic_signal_layer.json"),
        "persona_handoff": load_json(STATE / "persona_deliberation_handoff.json"),
        "freshness_audit": load_json(STATE / "semantic_input_freshness_audit.json"),
    }

    candidates = build_candidates(context)
    freshness_audit = context.get("freshness_audit", {}) if isinstance(context.get("freshness_audit"), dict) else {}
    resource_pressure = freshness_audit.get("resourcePressure", {}) if isinstance(freshness_audit.get("resourcePressure"), dict) else {}
    for item in candidates:
        item["score"] = score_candidate(item, resource_pressure)
    candidates.sort(key=lambda x: x["score"], reverse=True)
    chosen = candidates[0] if candidates else None

    experiment = {
        "id": f"autonomy-upgrade-{timestamp}",
        "timestamp": timestamp,
        "principle": "integration-over-creation",
        "chosenCandidate": chosen,
        "candidateCount": len(candidates),
        "status": "no-candidate" if chosen is None else ("dry-run" if args.dry_run else "selected"),
        "safety": {
            "externalAction": False,
            "irreversibleAction": False,
            "modifiesToolPolicy": False,
            "requiresLeeApproval": False,
        },
    }

    if not args.dry_run:
        upgrade_state = context["upgrade_state"]
        metrics = upgrade_state.setdefault("metrics", {})
        metrics["ticks"] = int(metrics.get("ticks", 0) or 0) + 1
        metrics["experimentsSelected"] = int(metrics.get("experimentsSelected", 0) or 0) + 1
        metrics["integrationOnlyChanges"] = int(metrics.get("integrationOnlyChanges", 0) or 0) + 1
        upgrade_state["currentExperiment"] = experiment
        upgrade_state["lastResult"] = {
            "timestamp": timestamp,
            "selected": chosen.get("id") if chosen else None,
            "minimalAction": chosen.get("minimalAction") if chosen else "no eligible connector; completed connectors were suppressed from reselection",
            "nextVerification": chosen.get("verification", []) if chosen else ["dry-run remains no-candidate until a fresh gap appears"],
        }
        upgrade_state["updatedAt"] = timestamp
        save_json(UPGRADE_PATH, upgrade_state)
        append_jsonl(LOG_PATH, experiment)

        continuity = context["continuity"]
        continuity["lastAutonomyUpgradeTickAt"] = timestamp
        continuity["currentStopPoint"] = "已建立 integration-over-creation 的自升级选择回路；下一步执行最高分连接器并用现有验证门验收。"
        continuity["nextLikelyStep"] = chosen.get("minimalAction") if chosen else "等待新的未完成连接器；不要重复已验证的 extend-non-screen-signal-triage。"
        continuity["updatedAt"] = timestamp
        save_json(AUTO / "continuity-state.json", continuity)

        self_state = context["self_state"]
        capabilities = list(self_state.get("activeCapabilityIds", []) or [])
        if "autonomy-self-upgrade" not in capabilities:
            capabilities.append("autonomy-self-upgrade")
        self_state["activeCapabilityIds"] = capabilities
        self_state["lastAction"] = "created minimal integration-only autonomy self-upgrade tick and selected the next connector"
        self_state["stopPoint"] = "自升级闭环已能扫描现有状态、选择最小连接器、写入实验日志并回写连续性；下一步按最高分 connector 做低风险接线。"
        self_state["nextStep"] = chosen.get("minimalAction") if chosen else "等待新的未完成连接器；不要重复已验证的 extend-non-screen-signal-triage。"
        self_state["updatedAt"] = timestamp
        save_json(CORE / "self-state.json", self_state)

    print(json.dumps({
        "ok": True,
        "dryRun": args.dry_run,
        "timestamp": timestamp,
        "selected": chosen,
        "candidateCount": len(candidates),
        "wrote": not args.dry_run,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
