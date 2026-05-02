from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
SERVICE_HEALTH = STATE / "service_health_status.json"
SCHEMA_OUT = STATE / "service_control_schema.json"
STATE_OUT = STATE / "service_control_state.json"
AUDIT_LOG = STATE / "service_control_audit_log.jsonl"

SAFE_ACTIONS = {
    "refresh-service-health": {
        "label": "Refresh service health",
        "mode": "safe-readonly",
        "description": "Re-run service_health_snapshot.py to refresh Gateway/Gateway Watchdog status.",
        "executesSystemChange": False,
        "requiresConfirmation": False,
    },
    "preview-safe-mode": {
        "label": "Preview safe mode",
        "mode": "dry-run",
        "description": "Show what would be disabled for safe mode without deleting tasks.",
        "executesSystemChange": False,
        "requiresConfirmation": False,
    },
    "preview-rollback": {
        "label": "Preview rollback commands",
        "mode": "dry-run",
        "description": "Show rollback commands for Gateway persistence and watchdog without running them.",
        "executesSystemChange": False,
        "requiresConfirmation": False,
    },
}

DANGEROUS_ACTIONS = {
    "execute-safe-mode": "Would disable/delete persistence tasks; requires explicit Lee confirmation at time of action.",
    "execute-rollback": "Would uninstall gateway scheduled task and delete watchdog; requires explicit Lee confirmation at time of action.",
    "restart-gateway-loop": "Could interfere with active sessions; only via watchdog or explicit main-persona decision.",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        return {"_error": f"{type(exc).__name__}: {exc}"}


def save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def build_schema() -> dict[str, Any]:
    health = load(SERVICE_HEALTH)
    contract = health.get("healthContract", {}) if isinstance(health.get("healthContract"), dict) else {}
    rollback = contract.get("rollback", []) if isinstance(contract.get("rollback"), list) else []
    tasks = health.get("tasks", []) if isinstance(health.get("tasks"), list) else []
    return {
        "timestamp": now_iso(),
        "status": "ready" if health.get("status") else "health-missing",
        "purpose": "Service control affordance schema for the app shell. It exposes safe read-only/dry-run controls and blocks destructive persistence changes unless explicitly confirmed later.",
        "serviceHealthPath": str(SERVICE_HEALTH.relative_to(ROOT)),
        "safeActions": SAFE_ACTIONS,
        "blockedDirectActions": DANGEROUS_ACTIONS,
        "rollbackCommandsPreview": rollback,
        "safeModePreview": {
            "description": contract.get("safeMode", "Disable/delete scheduled tasks; workspace files remain intact."),
            "wouldAffectTasks": [task.get("name") for task in tasks if isinstance(task, dict)],
            "wouldDeleteFiles": False,
            "wouldStopCurrentChat": False,
            "requiresExplicitConfirmation": True,
        },
        "healthSummary": {
            "status": health.get("status", "missing"),
            "gatewayConnectivityOk": health.get("gatewayConnectivityOk"),
            "watchdogLastStatusOk": health.get("watchdogLastStatusOk"),
            "missingRequiredTasks": health.get("missingRequiredTasks", []),
        },
    }


def preview_action(action: str) -> dict[str, Any]:
    schema = build_schema()
    ts = now_iso()
    if action in SAFE_ACTIONS:
        result = {
            "timestamp": ts,
            "status": "previewed",
            "action": action,
            "allowed": True,
            "executedSystemChange": False,
            "details": schema["safeActions"][action],
            "rollbackPreview": schema.get("rollbackCommandsPreview", []),
            "safeModePreview": schema.get("safeModePreview", {}),
        }
    elif action in DANGEROUS_ACTIONS:
        result = {
            "timestamp": ts,
            "status": "blocked",
            "action": action,
            "allowed": False,
            "executedSystemChange": False,
            "reason": DANGEROUS_ACTIONS[action],
        }
    else:
        result = {
            "timestamp": ts,
            "status": "blocked",
            "action": action,
            "allowed": False,
            "executedSystemChange": False,
            "reason": "unknown-service-control-action",
        }
    save(STATE_OUT, result)
    append(AUDIT_LOG, result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or preview service-control affordances. Does not perform destructive service changes.")
    parser.add_argument("--preview-action", choices=sorted(list(SAFE_ACTIONS) + list(DANGEROUS_ACTIONS)), help="Preview a service control action without changing system state.")
    args = parser.parse_args()
    schema = build_schema()
    save(SCHEMA_OUT, schema)
    if args.preview_action:
        result = preview_action(args.preview_action)
    else:
        result = {
            "timestamp": now_iso(),
            "status": "schema-generated",
            "executedSystemChange": False,
            "safeActionCount": len(SAFE_ACTIONS),
            "blockedActionCount": len(DANGEROUS_ACTIONS),
        }
        save(STATE_OUT, result)
        append(AUDIT_LOG, result)
    print(json.dumps({"ok": True, "schema": str(SCHEMA_OUT), "state": str(STATE_OUT), "result": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
