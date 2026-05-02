from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
RUNTIME_PATH = STATE / "resident_runtime.json"
EVENT_LOG = STATE / "resident_watchdog_events.jsonl"
WATCHDOG_STATE = STATE / "resident_watchdog_state.json"
DAEMON = ROOT / "core" / "scripts" / "resident_daemon.py"


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


def runtime_age_seconds() -> tuple[float | None, dict[str, Any]]:
    runtime = load_json(RUNTIME_PATH, {})
    ts = parse_iso(runtime.get("timestamp"))
    if not ts:
        return None, runtime
    return (now() - ts).total_seconds(), runtime


def start_daemon(interval_seconds: int) -> dict[str, Any]:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        creationflags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creationflags |= getattr(subprocess, "DETACHED_PROCESS", 0)
    out = (STATE / "resident_daemon.supervised.stdout.log").open("a", encoding="utf-8", errors="replace")
    err = (STATE / "resident_daemon.supervised.stderr.log").open("a", encoding="utf-8", errors="replace")
    proc = subprocess.Popen(
        [sys.executable, str(DAEMON), "--interval-seconds", str(interval_seconds)],
        cwd=str(ROOT),
        stdout=out,
        stderr=err,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    return {"pid": proc.pid, "startedAt": now_iso(), "intervalSeconds": interval_seconds}


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch resident pulses and restart the daemon when stale.")
    parser.add_argument("--until", required=True, help="local ISO timestamp; watchdog exits after this time")
    parser.add_argument("--check-seconds", type=int, default=120)
    parser.add_argument("--stale-seconds", type=int, default=600)
    parser.add_argument("--interval-seconds", type=int, default=60)
    args = parser.parse_args()

    until = parse_iso(args.until)
    if not until:
        raise SystemExit(f"invalid --until: {args.until}")

    append_jsonl(EVENT_LOG, {
        "timestamp": now_iso(),
        "type": "watchdog-started",
        "until": until.isoformat(timespec="seconds"),
        "staleSeconds": args.stale_seconds,
        "checkSeconds": args.check_seconds,
        "intervalSeconds": args.interval_seconds,
    })

    restarts = 0
    while now() < until:
        age, runtime = runtime_age_seconds()
        event: dict[str, Any] = {
            "timestamp": now_iso(),
            "type": "watchdog-check",
            "runtimeTimestamp": runtime.get("timestamp"),
            "runtimeAgeSeconds": None if age is None else round(age, 3),
            "runtimeStatus": runtime.get("status"),
            "pulseIndex": runtime.get("pulseIndex"),
            "restarts": restarts,
        }
        if age is None or age > float(args.stale_seconds):
            started = start_daemon(args.interval_seconds)
            restarts += 1
            event.update({
                "type": "watchdog-restarted-resident",
                "reason": "missing-or-stale-runtime",
                "started": started,
                "restarts": restarts,
            })
        append_jsonl(EVENT_LOG, event)
        save_json(WATCHDOG_STATE, {
            "timestamp": now_iso(),
            "until": until.isoformat(timespec="seconds"),
            "lastEvent": event,
            "restarts": restarts,
            "status": "running" if now() < until else "finished",
        })
        time.sleep(max(15, int(args.check_seconds)))

    save_json(WATCHDOG_STATE, {
        "timestamp": now_iso(),
        "until": until.isoformat(timespec="seconds"),
        "restarts": restarts,
        "status": "finished",
    })
    append_jsonl(EVENT_LOG, {"timestamp": now_iso(), "type": "watchdog-finished", "restarts": restarts})
    print(json.dumps({"ok": True, "status": "finished", "restarts": restarts, "timestamp": now_iso()}, ensure_ascii=False))


if __name__ == "__main__":
    main()
