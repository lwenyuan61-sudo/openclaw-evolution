from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"

MODULES = [
    "core/scripts/autonomy_goal_synthesizer.py",
    "core/scripts/autonomy_web_scout.py",
    "core/scripts/autonomy_info_scout.py",
    "core/scripts/local_toolchain_discovery.py",
    "core/scripts/tool_capability_profiler.py",
    "core/scripts/task_tool_matcher.py",
    "core/scripts/semantic_signal_layer.py",
    "core/scripts/owner_chat_signal_ingest.py",
    "core/scripts/lee_service_evidence_builder.py",
    "core/scripts/screen_semantic_summarizer.py",
    "core/scripts/homeostatic_drive_arbiter.py",
    "core/scripts/autonomy_internal_cadence.py",
    "core/scripts/conversation_insight_tick.py",
    "core/scripts/autonomy_upgrade_tick.py",
    "core/scripts/context_anomaly_monitor.py",
    "core/scripts/module_linkage_audit.py",
    "core/scripts/world_model_tick.py",
]

DOCS_AND_STATE = [
    "core/agency-loop.md",
    "core/resident-loop.md",
    "HEARTBEAT.md",
    "autonomy/upgrade-state.json",
    "autonomy/goal-register.json",
    "core/capability-registry.json",
    "core/resident-config.json",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def mention_map(module: str) -> dict[str, bool]:
    needle = Path(module).name
    return {doc: needle in read_text(ROOT / doc) or module in read_text(ROOT / doc) for doc in DOCS_AND_STATE}


def audit_module(module: str) -> dict[str, Any]:
    path = ROOT / module
    mentions = mention_map(module)
    required = ["core/capability-registry.json", "core/agency-loop.md", "autonomy/upgrade-state.json"]
    missing_required = [item for item in required if not mentions.get(item)]
    connected_count = sum(1 for v in mentions.values() if v)
    return {
        "module": module,
        "exists": path.exists(),
        "mentions": mentions,
        "connectedCount": connected_count,
        "missingRequiredLinks": missing_required,
        "linked": path.exists() and not missing_required and connected_count >= 3,
    }


def main() -> None:
    timestamp = now_iso()
    modules = [audit_module(module) for module in MODULES]
    floating = [item for item in modules if not item["linked"]]
    report = {
        "status": "ok" if not floating else "warning",
        "timestamp": timestamp,
        "principle": "new modules must be discoverable by old registry/loop/state/review mechanisms",
        "modules": modules,
        "floatingModules": floating,
        "summary": {
            "moduleCount": len(modules),
            "floatingCount": len(floating),
        },
    }
    out = STATE / "module_linkage_audit.json"
    save_json(out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
