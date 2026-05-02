from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
OPENCLAW_HOME = Path.home() / ".openclaw"
GATEWAY_CMD = OPENCLAW_HOME / "gateway.cmd"
STATUS_PATH = STATE / "gateway_watchdog_status.json"
LOG_PATH = STATE / "gateway_watchdog_log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def port_open(host: str = "127.0.0.1", port: int = 18789, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def append_log(entry: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def save_status(entry: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(entry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def start_gateway() -> dict:
    if not GATEWAY_CMD.exists():
        return {"started": False, "error": f"missing {GATEWAY_CMD}"}
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(subprocess, "DETACHED_PROCESS", 0)
    proc = subprocess.Popen(
        [str(GATEWAY_CMD)],
        cwd=str(OPENCLAW_HOME),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=creationflags,
    )
    return {"started": True, "pid": proc.pid, "command": str(GATEWAY_CMD)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true", help="Only report status; do not start gateway")
    parser.add_argument("--port", type=int, default=18789)
    args = parser.parse_args()

    before = port_open(port=args.port)
    action = "none"
    start_result = None
    if before:
        status = "ok"
    elif args.check_only:
        status = "down-check-only"
        action = "would-start"
    else:
        action = "start-gateway"
        start_result = start_gateway()
        status = "started" if start_result.get("started") else "start-failed"

    entry = {
        "timestamp": now_iso(),
        "port": args.port,
        "gatewayReachableBefore": before,
        "action": action,
        "status": status,
        "startResult": start_result,
        "policy": "local watchdog: start gateway.cmd only when loopback port is closed; no external network writes",
    }
    save_status(entry)
    append_log(entry)
    print(json.dumps(entry, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
