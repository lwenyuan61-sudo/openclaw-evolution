from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return load_json(path)


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", help="optional JSON report output path")
    args = parser.parse_args()

    self_state = load_json(CORE / "self-state.json")
    session_mode = load_json(CORE / "session-mode.json")
    attention = load_json(CORE / "attention-state.json")
    organ_registry = load_json(CORE / "organ-registry.json")
    body_state = load_json(CORE / "body-state.json")
    action_state = load_optional_json(CORE / "action-state.json") or {}
    perception_state = load_optional_json(CORE / "perception-state.json") or {}
    learning_state = load_json(CORE / "learning-state.json")
    continuity = load_json(AUTO / "continuity-state.json")
    wake_model_exists = (CORE / "wake-model.md").exists()
    effort_budget = load_optional_json(CORE / "effort-budget.json")
    procedural_memory = load_optional_json(CORE / "procedural-memory.json")
    signal_probe_config = load_optional_json(CORE / "signal-probe-config.json")
    upgrade_state = load_optional_json(AUTO / "upgrade-state.json")
    experiment_log_path = AUTO / "experiment-log.jsonl"

    errors: list[str] = []
    warnings: list[str] = []

    if self_state.get("currentFocus") != continuity.get("currentFocus"):
        errors.append("self-state.currentFocus 与 continuity-state.currentFocus 不一致")
    if self_state.get("currentMode") != session_mode.get("mode"):
        errors.append("self-state.currentMode 与 session-mode.mode 不一致")

    attention_slots = attention.get("attentionSlots", [])
    if len(attention_slots) > 3:
        warnings.append("attention slots 超过 3，可能开始失去有限意识窗口")

    pipeline = self_state.get("decisionPipeline", [])
    if not wake_model_exists:
        errors.append("缺少 core/wake-model.md")
    for required in [
        "restore-self",
        "apply-homeostasis-gate",
        "restore-effort-budget",
        "route-event",
        "match-procedural-memory",
        "verify",
        "write-back",
    ]:
        if required not in pipeline:
            errors.append(f"decisionPipeline 缺少关键步骤: {required}")

    organ_names = {item.get("name") for item in organ_registry.get("organs", [])}
    for required in ["camera-io", "audio-io", "voice-loop", "device-state", "screen-state", "signal-bus"]:
        if required not in organ_names:
            warnings.append(f"organ-registry 未注册 {required}")

    body_organs = body_state.get("organs", {})
    for required in ["camera", "microphone", "speaker", "screen-state"]:
        if required not in body_organs:
            warnings.append(f"body-state 未声明 {required} 器官")

    if not self_state.get("nextStep"):
        warnings.append("self-state 缺少 nextStep，可能增加下一轮重新开机感")

    wake_policy = self_state.get("wakePolicy", {})
    if wake_policy.get("cronRequired") is not False:
        warnings.append("wakePolicy 未显式声明 cronRequired=false")

    if not perception_state.get("updatedAt"):
        warnings.append("perception-state 尚未更新，现实信号层可能还没真正接上")
    if not perception_state.get("lastProbeSignals") is not None:
        warnings.append("perception-state 缺少 lastProbeSignals，局部最新信号可能无法低成本路由")
    if not action_state.get("actuatorStatus"):
        warnings.append("action-state 尚未建立 actuatorStatus，现实动作桥可能还没真正接上")

    counters = learning_state.get("counters", {})
    if counters.get("lowValueWakeCount", 0) > counters.get("highValueWakeCount", 0) + counters.get("mediumValueWakeCount", 0):
        warnings.append("近期低价值 wake 偏多，建议优先修正路由或稳态而不是继续扩层")

    if not effort_budget:
        warnings.append("缺少 effort-budget.json，无法把高成本思考限制在必要场景")
    else:
        if not effort_budget.get("eventBudgets"):
            warnings.append("effort-budget.json 缺少 eventBudgets")
        if not effort_budget.get("actionCosts"):
            warnings.append("effort-budget.json 缺少 actionCosts")

    if not procedural_memory:
        warnings.append("缺少 procedural-memory.json，重复成功还没有可编译的习惯层")
    elif not procedural_memory.get("habits"):
        warnings.append("procedural-memory.json 还没有种子习惯")

    if not signal_probe_config:
        warnings.append("缺少 signal-probe-config.json，workspace 变化可能混入自写状态噪声")
    else:
        ignored_roots = set(signal_probe_config.get("ignoreRoots", []))
        if "state" not in ignored_roots:
            warnings.append("signal-probe-config.json 未忽略 state/，容易把自写 runtime 当外部信号")

    if not upgrade_state:
        warnings.append("缺少 autonomy/upgrade-state.json，自主性升级还没有可恢复状态")
    else:
        if upgrade_state.get("principle") != "integration-over-creation":
            warnings.append("upgrade-state 未声明 integration-over-creation，可能偏向凭空新增而不是连接现有回路")
        if not upgrade_state.get("loop"):
            warnings.append("upgrade-state 缺少 loop，自升级闭环不可复盘")
    if not experiment_log_path.exists():
        warnings.append("缺少 autonomy/experiment-log.jsonl，自升级实验还没有 append-only 证据链")

    report = {
        "status": "error" if errors else ("warning" if warnings else "ok"),
        "timestamp": now_iso(),
        "errors": errors,
        "warnings": warnings,
        "summary": {
            "focus": self_state.get("currentFocus"),
            "mode": self_state.get("currentMode"),
            "attentionSlotCount": len(attention_slots),
            "registeredOrgans": len(organ_registry.get("organs", [])),
        },
    }

    if args.write:
        out = Path(args.write)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
