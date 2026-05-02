from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
PERMISSION_PATH = STATE / "app_permission_matrix.json"
CONTROL_SCHEMA_PATH = STATE / "app_control_schema.json"
CONTROL_STATE_PATH = STATE / "app_control_state.json"
AUDIT_LOG = STATE / "app_control_audit_log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def control_for(cap: dict[str, Any]) -> dict[str, Any]:
    cap_id = cap.get("id")
    category = cap.get("category")
    allowed = bool(cap.get("allowedNow"))
    mode = str(cap.get("currentMode") or "unknown")
    sensitive = category in {"audio-privacy", "vision-privacy", "real-world-actuation", "outbound-communication", "persistence"}
    dry_run_only = (not allowed) or mode in {"disabled", "manual-only", "approval-gated", "simulator-first", "resource-gated"}
    if cap_id in {"gateway-autostart", "resident-self-evolution-wake"}:
        dry_run_only = False
    if cap_id == "physical-actuation":
        dry_run_only = False  # simulator action allowed; real devices remain blocked by policy tier.
    return {
        "id": cap_id,
        "label": str(cap_id).replace("-", " ").title(),
        "category": category,
        "currentMode": mode,
        "allowedNow": allowed,
        "sensitive": sensitive,
        "defaultEnabled": allowed and not sensitive,
        "dryRunOnly": dry_run_only,
        "requiresConfirmation": sensitive,
        "reason": cap.get("reason"),
        "constraints": cap.get("constraints", []),
        "rollback": cap.get("rollback", []),
        "auditState": cap.get("auditState"),
    }


def main() -> None:
    ts = now_iso()
    perm = load(PERMISSION_PATH, {})
    previous_state = load(CONTROL_STATE_PATH, {})
    capabilities = [c for c in perm.get("capabilities", []) or [] if isinstance(c, dict)]
    controls = [control_for(c) for c in capabilities]
    schema = {
        "timestamp": ts,
        "status": "ok",
        "purpose": "Dry-run control schema for Local Evolution Agent Desktop Companion. UI can render these controls without performing sensitive actions.",
        "globalPolicy": perm.get("globalPolicy", {}),
        "controls": controls,
        "safeActions": [
            "refresh-dashboard",
            "run-resource-check",
            "run-consistency-check",
            "open-report",
            "simulate-physical-action"
        ],
        "blockedDirectActions": [
            "enable-always-on-mic",
            "enable-camera-continuous",
            "send-external-message",
            "real-physical-actuation",
            "paid-api-call",
            "gpu-heavy-local-model"
        ],
        "auditLog": str(AUDIT_LOG.relative_to(ROOT)),
    }
    state = {
        "timestamp": ts,
        "status": "ready",
        "enabledControls": [c["id"] for c in controls if c.get("defaultEnabled")],
        "dryRunControls": [c["id"] for c in controls if c.get("dryRunOnly")],
        "confirmationRequired": [c["id"] for c in controls if c.get("requiresConfirmation")],
        "pauseAll": bool(previous_state.get("pauseAll", False)),
        "lastAction": "schema-generated-no-sensitive-action-executed",
    }
    save(CONTROL_SCHEMA_PATH, schema)
    save(CONTROL_STATE_PATH, state)
    append(AUDIT_LOG, {"timestamp": ts, "event": "schema-generated", "sensitiveActionExecuted": False})
    print(json.dumps({"ok": True, "schema": str(CONTROL_SCHEMA_PATH), "state": str(CONTROL_STATE_PATH), "controlCount": len(controls)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
