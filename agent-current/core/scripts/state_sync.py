from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    self_state_path = CORE / "self-state.json"
    session_mode_path = CORE / "session-mode.json"
    continuity_path = AUTO / "continuity-state.json"
    self_direction_path = AUTO / "self-direction-state.json"
    deliberation_path = CORE / "deliberation-state.json"

    self_state = load_json(self_state_path)
    session_mode = load_json(session_mode_path)
    continuity = load_json(continuity_path)
    self_direction = load_json(self_direction_path) if self_direction_path.exists() else {}
    deliberation = load_json(deliberation_path) if deliberation_path.exists() else {}

    timestamp = now_iso()

    self_state["currentMode"] = session_mode.get("mode", self_state.get("currentMode"))
    if self_direction:
        self_state["currentTrackId"] = self_direction.get("currentTrackId", self_state.get("currentTrackId"))
        self_state["activeCapabilityIds"] = self_direction.get("activeCapabilityIds", self_state.get("activeCapabilityIds", []))
    if deliberation:
        self_state["currentLayer"] = deliberation.get("currentLayer", self_state.get("currentLayer"))
    self_state["updatedAt"] = timestamp

    continuity["currentFocus"] = self_state.get("currentFocus")
    continuity["currentTrackId"] = self_state.get("currentTrackId", continuity.get("currentTrackId"))
    continuity["activeCapabilityIds"] = self_state.get("activeCapabilityIds", continuity.get("activeCapabilityIds", []))
    continuity["lastAction"] = self_state.get("lastAction")
    continuity["currentStopPoint"] = self_state.get("stopPoint")
    continuity["nextLikelyStep"] = self_state.get("nextStep")
    continuity["modeReason"] = session_mode.get("modeReason", continuity.get("modeReason"))
    continuity["updatedAt"] = timestamp

    save_json(self_state_path, self_state)
    save_json(continuity_path, continuity)

    print(json.dumps({
        "synced": True,
        "selfState": str(self_state_path),
        "continuityState": str(continuity_path),
        "timestamp": timestamp,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
