from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
HEALTH_PATH = STATE / "context_health.json"
HANDOFF_PATH = STATE / "context_renewal_handoff.md"
UPGRADE_PATH = AUTO / "upgrade-state.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def classify(ratio: float) -> tuple[str, str]:
    if ratio >= 0.94:
        return "renew-recommended", "context usage is close to hard limit; compact and renew conversation"
    if ratio >= 0.90:
        return "critical", "context usage is critical; prepare renewal handoff now"
    if ratio >= 0.80:
        return "warn", "context usage is high; monitor and compact soon"
    return "ok", "context usage is within normal range"


def ensure_handoff_note(status: str, ratio: float, used: int, limit: int) -> None:
    if status not in {"critical", "renew-recommended"}:
        return
    existing = HANDOFF_PATH.read_text(encoding="utf-8", errors="replace") if HANDOFF_PATH.exists() else ""
    marker = "## Context anomaly monitor"
    if marker in existing:
        return
    note = f"""

{marker}

- Detected context pressure: {used}/{limit} ({ratio:.1%}), status={status}.
- If this session is renewed, resume from `memory/2026-04-25.md`, `autonomy/upgrade-state.json`, and this handoff file.
- Continue self-upgrade through resident internal cadence; keep cron as disabled fallback only.
"""
    HANDOFF_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HANDOFF_PATH.open("a", encoding="utf-8") as handle:
        handle.write(note)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--context-used", type=int, required=True)
    parser.add_argument("--context-limit", type=int, required=True)
    parser.add_argument("--source", default="manual-session-status")
    args = parser.parse_args()

    timestamp = now_iso()
    ratio = args.context_used / args.context_limit if args.context_limit else 0.0
    status, recommendation = classify(ratio)
    ensure_handoff_note(status, ratio, args.context_used, args.context_limit)

    health = {
        "timestamp": timestamp,
        "source": args.source,
        "contextUsed": args.context_used,
        "contextLimit": args.context_limit,
        "ratio": round(ratio, 4),
        "status": status,
        "recommendation": recommendation,
        "handoffPath": str(HANDOFF_PATH.relative_to(ROOT)),
    }
    save_json(HEALTH_PATH, health)

    upgrade = load_json(UPGRADE_PATH, {})
    upgrade["contextAnomalyMonitor"] = {
        "enabled": True,
        "script": "core/scripts/context_anomaly_monitor.py",
        "lastRun": health,
        "thresholds": {
            "warn": 0.80,
            "critical": 0.90,
            "renewRecommended": 0.94,
        },
        "principle": "detect context/data pressure early, compact durable state, and recommend renewal before hard limits break continuity",
    }
    upgrade["updatedAt"] = timestamp
    save_json(UPGRADE_PATH, upgrade)

    append_jsonl(LOG_PATH, {
        "id": "context-anomaly-monitor-" + timestamp,
        "timestamp": timestamp,
        "type": "context-anomaly-monitor",
        "status": status,
        "ratio": round(ratio, 4),
        "recommendation": recommendation,
    })

    print(json.dumps(health, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
