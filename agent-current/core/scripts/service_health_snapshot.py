from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
OUT = STATE / "service_health_status.json"

TASKS = [
    {
        "id": "openclaw-gateway",
        "name": "OpenClaw Gateway",
        "purpose": "Keep the local OpenClaw Gateway available after reboot/login.",
        "rollback": "openclaw gateway uninstall",
        "required": True,
    },
    {
        "id": "openclaw-gateway-watchdog",
        "name": "OpenClaw Gateway Watchdog",
        "purpose": "Every 2 minutes, check loopback gateway port and restart gateway only if closed.",
        "rollback": "schtasks /Delete /TN \"OpenClaw Gateway Watchdog\" /F",
        "required": True,
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdoutTail": p.stdout[-2000:],
            "stderrTail": p.stderr[-2000:],
        }
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "stdoutTail": "", "stderrTail": ""}


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def task_snapshot(task: dict[str, Any]) -> dict[str, Any]:
    query = run(["schtasks.exe", "/Query", "/TN", task["name"], "/FO", "LIST", "/V"])
    registered = query.get("ok") is True
    text = str(query.get("stdoutTail", ""))
    return {
        **task,
        "registered": registered,
        "queryReturnCode": query.get("returncode"),
        "queryOk": query.get("ok"),
        "nextRunHint": extract_hint(text, ["Next Run Time", "下次运行时间", "下次執行時間"]),
        "statusHint": extract_hint(text, ["Status", "状态", "狀態"]),
        "rawTail": text[-1000:],
    }


def extract_hint(text: str, keys: list[str]) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        for key in keys:
            if stripped.lower().startswith(key.lower()):
                return stripped
    return None


def main() -> None:
    gateway_status = run(["openclaw", "gateway", "status"], timeout=30)
    watchdog_status = load(STATE / "gateway_watchdog_status.json")
    tasks = [task_snapshot(t) for t in TASKS]
    missing = [t["name"] for t in tasks if t.get("required") and not t.get("registered")]
    gateway_text = str(gateway_status.get("stdoutTail", ""))
    watchdog_ok = watchdog_status.get("status") == "ok" or watchdog_status.get("gatewayReachableBefore") is True
    gateway_ok = (
        (gateway_status.get("ok") is True and ("Connectivity probe: ok" in gateway_text or "Gateway:" in gateway_text))
        or watchdog_status.get("gatewayReachableBefore") is True
    )
    status = "ok" if not missing and gateway_ok and watchdog_ok else "warn"
    doc = {
        "timestamp": now_iso(),
        "status": status,
        "gatewayConnectivityOk": gateway_ok,
        "watchdogLastStatusOk": watchdog_ok,
        "missingRequiredTasks": missing,
        "tasks": tasks,
        "gatewayStatusReturnCode": gateway_status.get("returncode"),
        "gatewayStatusCommandOk": gateway_status.get("ok"),
        "gatewayStatusTail": gateway_status.get("stdoutTail", "")[-2000:],
        "watchdogStatus": watchdog_status,
        "healthContract": {
            "loopbackOnly": True,
            "watchdogPeriodMinutes": 2,
            "restartPolicy": "Only start gateway.cmd when loopback port check says closed; no external network writes.",
            "rollback": [t["rollback"] for t in TASKS],
            "safeMode": "Disable/delete the scheduled tasks; core workspace files remain intact.",
        },
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": status == "ok", "status": status, "out": str(OUT), "missingRequiredTasks": missing}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
