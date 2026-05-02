from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
LOG_PATH = AUTO / "experiment-log.jsonl"


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


def existing_ids(register: dict[str, Any]) -> set[str]:
    return {item.get("id") for item in register.get("candidates", []) if isinstance(item, dict) and item.get("id")}


def synthesize_candidates(self_state: dict[str, Any], upgrade: dict[str, Any], learning: dict[str, Any], register: dict[str, Any], semantic_layer: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ids = existing_ids(register)
    # Suppress already-verified connector/request ids as well as existing
    # goal-register ids. Otherwise a completed semantic request can be
    # regenerated on the next cadence and re-create a maintain/repair loop.
    for item in upgrade.get("completedConnectors", []) or []:
        if isinstance(item, dict) and item.get("id"):
            ids.add(str(item.get("id")))
        elif item:
            ids.add(str(item))
    for key in ("lastConnectorCompleted", "lastVerification"):
        item = upgrade.get(key)
        if isinstance(item, dict):
            for value_key in ("id", "selected"):
                if item.get(value_key):
                    ids.add(str(item.get(value_key)))
    open_loops = "\n".join(str(x) for x in self_state.get("openLoops", []) if x)
    final_signals = upgrade.get("valuePolicy", {}).get("finalFormSignals", []) if isinstance(upgrade.get("valuePolicy"), dict) else []
    counters = learning.get("counters", {}) if isinstance(learning.get("counters"), dict) else {}
    candidates: list[dict[str, Any]] = []

    def add(item: dict[str, Any], reason: str, evidence: list[str] | None = None) -> None:
        if item["id"] not in ids:
            item["generationReason"] = reason
            item["generationEvidence"] = evidence or []
            candidates.append(item)

    semantic_layer = semantic_layer or {}
    local_tools = load_json(STATE / "local_toolchain_discovery.json", {})
    local_opportunities = local_tools.get("opportunities", []) if isinstance(local_tools.get("opportunities"), list) else []
    if local_opportunities:
        for opportunity in local_opportunities[:5]:
            if not isinstance(opportunity, dict) or not opportunity.get("id"):
                continue
            opp_id = str(opportunity.get("id"))
            add({
                "id": opp_id,
                "title": str(opportunity.get("title") or opp_id),
                "focus": "turn installed local software into discoverable, scriptable resident/main-persona toolchains",
                "goal": str(opportunity.get("reason") or "本机已有高价值可脚本化工具，但尚未接入能力注册和调用链。"),
                "subgoal": "把本机已安装工具从偶然发现变成 local_toolchain_discovery -> goal-register -> capability-registry 的持续链路。",
                "nextConcreteStep": str(opportunity.get("nextConcreteStep") or "为该本地工具创建最小 probe/wrapper/registry/toolchain 连接器并验证。"),
                "leeValue": 0.96,
                "continuityWeight": 0.9,
                "feasibility": 0.86,
                "learningLeverage": 0.94,
                "noiseRisk": 0.14,
                "relatedCapabilities": ["autonomy-self-upgrade", "local-toolchain-discovery", "reality-bridge"],
                "status": "active",
                "source": "self-synthesized-local-toolchain-discovery",
                "sourceObservation": "local-toolchain-discovery",
                "createdAt": now_iso(),
            }, "local_toolchain_discovery found unregistered high-value installed tool", [f"toolId={opportunity.get('toolId')}", f"valueScore={opportunity.get('valueScore')}"])

    semantic_requests = semantic_layer.get("candidateRequests", []) if isinstance(semantic_layer.get("candidateRequests"), list) else []
    semantic_pressure = float(semantic_layer.get("semanticPressure", 0.0) or 0.0)
    high_value_semantic_request = any(
        isinstance(request, dict) and float(request.get("leeValue", 0.0) or 0.0) >= 0.95
        for request in semantic_requests
    )
    if semantic_requests and (semantic_pressure >= 0.55 or high_value_semantic_request):
        for request in semantic_requests[:5]:
            if not isinstance(request, dict) or not request.get("id"):
                continue
            req_id = str(request.get("id"))
            add({
                "id": req_id,
                "title": str(request.get("title") or req_id),
                "focus": "turn complex resident signals into concrete, verifiable autonomy connector candidates",
                "goal": str(request.get("gap") or "复杂信号已经形成语义压力，需要进入目标池和验证闭环。"),
                "subgoal": str(request.get("gap") or "把 semantic_signal_layer 的 candidateRequests 接进候选生成/升级选择。"),
                "nextConcreteStep": str(request.get("nextConcreteStep") or "为该 semantic candidate request 执行一个最小可验证连接器。"),
                "leeValue": float(request.get("leeValue", 0.92) or 0.92),
                "continuityWeight": 0.95,
                "feasibility": float(request.get("feasibility", 0.78) or 0.78),
                "learningLeverage": float(request.get("learningLeverage", 0.9) or 0.9),
                "noiseRisk": float(request.get("noiseRisk", 0.2) or 0.2),
                "relatedCapabilities": ["autonomy-self-upgrade", "conversation-insight-ingestion", "world-modeling", "adaptive-learning"],
                "status": "active",
                "source": "self-synthesized-semantic-signal-layer",
                "sourceObservation": request.get("sourceObservation"),
                "semanticPressure": semantic_pressure,
                "createdAt": now_iso(),
            }, "semantic_signal_layer emitted concrete candidate request", [f"semanticPressure={semantic_pressure}", f"sourceObservation={request.get('sourceObservation')}"])

    if "less dependence on external cron" in final_signals or "cron" in open_loops:
        add({
            "id": "resident-internal-cadence-evolution",
            "title": "resident 内化节奏进化",
            "focus": "make autonomous upgrade timing emerge from resident state instead of fixed external schedules",
            "goal": "让the agent的持续升级节奏由状态、价值、疲劳与机会共同决定，而不是死的 cron/固定分钟数",
            "subgoal": "把静默窗口、升级间隔、价值压力、噪声压力和 handoff 状态接入同一个 adaptive timing gate",
            "nextConcreteStep": "让 autonomy_internal_cadence 计算 dynamicIntervalSeconds，并把 selected pressure 写入 upgrade-state",
            "leeValue": 1.0,
            "continuityWeight": 0.98,
            "feasibility": 0.9,
            "learningLeverage": 1.0,
            "noiseRisk": 0.18,
            "relatedCapabilities": ["autonomy-self-upgrade", "continuity-core", "initiative-control", "adaptive-learning"],
            "status": "active",
            "source": "self-synthesized-from-Lee-final-form",
        }, "final-form signal asks for resident-owned timing instead of cron", ["less dependence on external cron"])

    if "new modules fully linked to old modules" in final_signals or "更多 wake 文件" in open_loops:
        add({
            "id": "module-linkage-auditor",
            "title": "新旧模块链接审计器",
            "focus": "ensure every new module is wired into capability registry, agency loop, learning, verification, and continuity",
            "goal": "防止新能力悬空，让每个新增脚本/状态/规则都能被旧回路发现、调用、验证和回写",
            "subgoal": "扫描新增模块是否具备 registry / loop / verification / state-sync / experiment-log 五类连接",
            "nextConcreteStep": "实现一个只读 module_linkage_audit.py，输出悬空模块和建议接线，不直接大改",
            "leeValue": 0.98,
            "continuityWeight": 0.96,
            "feasibility": 0.88,
            "learningLeverage": 0.97,
            "noiseRisk": 0.16,
            "relatedCapabilities": ["autonomy-self-upgrade", "continuity-core", "adaptive-learning"],
            "status": "active",
            "source": "self-synthesized-from-Lee-final-form",
        }, "final-form signal requires new modules to be discoverable by old loops", ["new modules fully linked to old modules"])

    verified = int(counters.get("deliberationEpisodesVerified", 0) or 0)
    compiled = int(counters.get("deliberationPatternsCompiled", 0) or 0)
    if verified >= compiled + 4:
        add({
            "id": "s2-to-s1-compiler-pressure",
            "title": "S2 到 S1 编译压力释放",
            "focus": "turn verified deep reasoning outcomes into cheap resident habits faster",
            "goal": "减少重复深推理，把已验证的高价值判断压缩成小脑习惯",
            "subgoal": "用 learning-state 的 verified/compiled 差值驱动 procedural-memory 编译优先级",
            "nextConcreteStep": "在 autonomy_upgrade_tick 中把 verified-minus-compiled 作为候选评分压力",
            "leeValue": 0.93,
            "continuityWeight": 0.92,
            "feasibility": 0.9,
            "learningLeverage": 0.96,
            "noiseRisk": 0.12,
            "relatedCapabilities": ["adaptive-learning", "deliberation-engine", "autonomy-self-upgrade"],
            "status": "active",
            "source": "self-synthesized-from-learning-pressure",
        }, "verified S2 count is outpacing compiled patterns", [f"verified={verified}", f"compiled={compiled}"])

    if not candidates:
        add({
            "id": "creative-self-review-loop",
            "title": "创造性自审回路",
            "focus": "periodically invent one useful integration question instead of only following fixed backlog items",
            "goal": "让the agent能主动提出整改目标，并把它们接入目标池、评分、验证和回写",
            "subgoal": "从 openLoops、recentLessons、failed gates、Lee final form signals 中生成候选整改目标",
            "nextConcreteStep": "保持 autonomy_goal_synthesizer 作为目标池补充入口，并记录每次生成理由",
            "leeValue": 0.9,
            "continuityWeight": 0.9,
            "feasibility": 0.95,
            "learningLeverage": 0.9,
            "noiseRisk": 0.1,
            "relatedCapabilities": ["autonomy-self-upgrade", "initiative-control"],
            "status": "active",
            "source": "self-synthesized-default",
        }, "no specific missing connector was available, so preserve a general creative self-review entry", ["fallback-no-new-specific-candidate"])

    return candidates


def main() -> None:
    timestamp = now_iso()
    self_state = load_json(CORE / "self-state.json")
    upgrade = load_json(AUTO / "upgrade-state.json")
    learning = load_json(CORE / "learning-state.json")
    semantic_layer = load_json(STATE / "semantic_signal_layer.json", {})
    register_path = AUTO / "goal-register.json"
    register = load_json(register_path)

    candidates = synthesize_candidates(self_state, upgrade, learning, register, semantic_layer)
    if candidates:
        register.setdefault("candidates", []).extend(candidates)
        register["updatedAt"] = timestamp
        save_json(register_path, register)

    synth_state = upgrade.setdefault("creativeGoalSynthesis", {})
    synth_state.update({
        "enabled": True,
        "lastRunAt": timestamp,
        "generatedCount": len(candidates),
        "generatedIds": [item["id"] for item in candidates],
        "lastGenerationReasons": {
            item["id"]: {
                "reason": item.get("generationReason"),
                "evidence": item.get("generationEvidence", []),
            }
            for item in candidates
        },
        "lastNoNewCandidateReason": None if candidates else "all currently synthesized goals already exist in goal-register or no final-form gap passed thresholds",
        "principle": "generate corrective goals from final-form pressure and current loop gaps, then route through existing goal/register/review mechanisms",
    })
    upgrade["updatedAt"] = timestamp
    save_json(AUTO / "upgrade-state.json", upgrade)

    entry = {
        "id": "creative-goal-synthesis-" + timestamp,
        "timestamp": timestamp,
        "type": "creative-goal-synthesis",
        "status": "generated" if candidates else "no-new-candidates",
        "generated": candidates,
        "generationReasons": {
            item["id"]: {
                "reason": item.get("generationReason"),
                "evidence": item.get("generationEvidence", []),
            }
            for item in candidates
        },
        "noNewCandidateReason": None if candidates else "all currently synthesized goals already exist in goal-register or no final-form gap passed thresholds",
        "principle": "creative additions must enter existing goal-register and verification loop",
    }
    append_jsonl(LOG_PATH, entry)

    print(json.dumps({
        "ok": True,
        "timestamp": timestamp,
        "generatedCount": len(candidates),
        "generatedIds": [item["id"] for item in candidates],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
