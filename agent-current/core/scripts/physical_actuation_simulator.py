from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
POLICY_PATH = STATE / "physical_actuation_policy.json"
ALLOWLIST_PATH = STATE / "physical_actuation_allowlist.json"
LOG_PATH = STATE / "physical_actuation_simulator_log.jsonl"
STATUS_PATH = STATE / "physical_actuation_simulator_status.json"
DISABLE_FLAG = STATE / "physical_actuation_disabled.flag"

REQUIRED_ACTION_FIELDS = {"id", "kind", "target", "operation"}


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


def tier_allowed(policy: dict, tier: str) -> tuple[bool, str]:
    if DISABLE_FLAG.exists():
        return False, "kill-switch-flag-present"
    for item in policy.get("tiers", []) or []:
        if isinstance(item, dict) and item.get("tier") == tier:
            if item.get("blocked"):
                return False, "tier-blocked"
            return bool(item.get("allowed")), "tier-policy"
    return False, "unknown-tier"


def classify_action(action: dict) -> str:
    if action.get("simulateOnly", True):
        return "T0"
    if action.get("kind") in {"query-status", "virtual-device", "desktop-reversible"}:
        return "T1"
    if action.get("kind") in {"real-device"}:
        return "T2"
    return "T3"


def validate_shape(action: dict) -> tuple[bool, str]:
    missing = sorted(REQUIRED_ACTION_FIELDS - set(action))
    if missing:
        return False, "missing-required-fields:" + ",".join(missing)
    action_id = str(action.get("id", ""))
    if not action_id or any(ch.isspace() for ch in action_id):
        return False, "invalid-id"
    if not isinstance(action.get("simulateOnly", True), bool):
        return False, "simulateOnly-must-be-boolean"
    return True, "schema-ok"


def validate_allowlist(action: dict, tier: str, allowlist: dict) -> tuple[bool, str]:
    """Validate target/operation against a simulator allowlist before any non-T0 path.

    This still never calls real devices; it only blocks unsafe or unknown intents early.
    """
    if tier == "T0":
        return True, "simulate-only-bypasses-device-allowlist"

    target = str(action.get("target", ""))
    operation = str(action.get("operation", ""))
    kind = str(action.get("kind", ""))
    devices = allowlist.get("devices", []) if isinstance(allowlist, dict) else []

    for device in devices:
        if not isinstance(device, dict) or device.get("id") != target:
            continue
        if tier not in (device.get("allowedTiers") or []):
            return False, "target-tier-not-allowed"
        if kind and kind not in (device.get("allowedKinds") or []):
            return False, "target-kind-not-allowed"
        if operation not in (device.get("allowedOperations") or []):
            return False, "operation-not-allowed"
        return True, "allowlist-ok"

    return False, "target-not-allowlisted"


def load_action(args: argparse.Namespace) -> dict:
    if args.action_file:
        action = load(Path(args.action_file), {})
    elif args.action_json:
        action = json.loads(args.action_json)
    else:
        action = {
            "id": "sample-light-toggle",
            "kind": "virtual-device",
            "target": "demo-lamp",
            "operation": "toggle",
            "simulateOnly": True,
        }
    if not isinstance(action, dict):
        raise ValueError("action must be a JSON object")
    return action


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run physical actuation simulator. Does not call real devices.")
    parser.add_argument("--action-json", help="JSON object describing intended action")
    parser.add_argument("--action-file", help="Path to JSON action file")
    args = parser.parse_args()

    action = load_action(args)
    policy = load(POLICY_PATH, {})
    allowlist = load(ALLOWLIST_PATH, {"devices": []})
    tier = str(action.get("tier") or classify_action(action))

    shape_ok, shape_reason = validate_shape(action)
    allowed, reason = tier_allowed(policy, tier)
    allowlist_ok, allowlist_reason = validate_allowlist(action, tier, allowlist) if shape_ok else (False, "schema-not-validated")
    final_allowed = bool(shape_ok and allowed and allowlist_ok)
    if not shape_ok:
        final_reason = shape_reason
    elif not allowed:
        final_reason = reason
    elif not allowlist_ok:
        final_reason = allowlist_reason
    else:
        final_reason = "schema-policy-allowlist-ok"

    outcome = {
        "timestamp": now_iso(),
        "status": "simulated" if final_allowed else "blocked",
        "tier": tier,
        "allowed": final_allowed,
        "reason": final_reason,
        "schema": {"ok": shape_ok, "reason": shape_reason},
        "allowlist": {"ok": allowlist_ok, "reason": allowlist_reason, "path": str(ALLOWLIST_PATH.relative_to(ROOT))},
        "action": action,
        "realDeviceCalled": False,
        "externalWrite": False,
        "verification": "schema-policy-allowlist-only",
    }
    save(STATUS_PATH, outcome)
    append(LOG_PATH, outcome)
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
