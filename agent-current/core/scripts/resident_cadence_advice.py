from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def derive_counts(perception: dict) -> tuple[int, int, str]:
    last_probe_signals = perception.get("lastProbeSignals") or []
    last_suppressed_signals = perception.get("lastSuppressedSignals") or []

    emitted = len(last_probe_signals)
    suppressed = len(last_suppressed_signals)
    source = "last-probe"

    if emitted == 0 and suppressed == 0:
        recent_signals = perception.get("recentSignals") or []
        recent_suppressed = perception.get("recentSuppressedSignals") or []
        emitted = sum(int(item.get("repeatCount", 1)) for item in recent_signals[-3:])
        suppressed = sum(int(item.get("repeatCount", 1)) for item in recent_suppressed[-3:])
        source = "recent-history"

    return emitted, suppressed, source


def derive_interval(default_interval: int, minimum_interval: int, maximum_interval: int, emitted: int, suppressed: int) -> tuple[int, str]:
    if emitted > suppressed:
        return clamp(default_interval // 2, minimum_interval, maximum_interval), "emitted-dominant"
    if suppressed > emitted:
        return clamp(default_interval * 2, minimum_interval, maximum_interval), "suppressed-dominant"
    return clamp(default_interval, minimum_interval, maximum_interval), "balanced-or-quiet"


def build_advice(emitted: int | None = None, suppressed: int | None = None) -> dict:
    config = load_json(CORE / "resident-config.json")
    perception = load_json(CORE / "perception-state.json")

    derived_emitted, derived_suppressed, count_source = derive_counts(perception)
    emitted_count = derived_emitted if emitted is None else emitted
    suppressed_count = derived_suppressed if suppressed is None else suppressed

    default_interval = int(config.get("intervalSeconds", 120))
    minimum_interval = int(config.get("minIntervalSeconds", default_interval))
    maximum_interval = int(config.get("maxIntervalSeconds", default_interval))
    interval_seconds, mode = derive_interval(
        default_interval,
        minimum_interval,
        maximum_interval,
        int(emitted_count),
        int(suppressed_count),
    )

    return {
        "intervalSeconds": interval_seconds,
        "reason": f"{mode} cadence advice from {count_source}",
        "mode": mode,
        "evidence": {
            "emittedSignals": int(emitted_count),
            "suppressedSignals": int(suppressed_count),
            "countSource": count_source,
            "lastSignalProbeAt": perception.get("lastSignalProbeAt"),
            "perceptionUpdatedAt": perception.get("updatedAt"),
        },
        "updatedAt": now_iso(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-path")
    parser.add_argument("--emitted", type=int)
    parser.add_argument("--suppressed", type=int)
    args = parser.parse_args()

    advice = build_advice(emitted=args.emitted, suppressed=args.suppressed)
    if args.write_path:
        save_json(ROOT / args.write_path, advice)
    print(json.dumps(advice, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
