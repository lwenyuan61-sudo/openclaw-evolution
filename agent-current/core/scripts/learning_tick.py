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
    learning_state_path = CORE / "learning-state.json"
    continuity_path = AUTO / "continuity-state.json"

    self_state = load_json(self_state_path)
    learning_state = load_json(learning_state_path)
    continuity = load_json(continuity_path)

    counters = learning_state.setdefault("counters", {})
    counters.setdefault("selfDirectedTicks", 0)
    counters["selfDirectedTicks"] += 1

    current_focus = self_state.get("currentFocus")
    focus_summary = learning_state.setdefault("focusPulseSummary", {
        "currentFocus": current_focus,
        "streak": 0,
    })
    if focus_summary.get("currentFocus") == current_focus:
        focus_summary["streak"] = int(focus_summary.get("streak", 0)) + 1
    else:
        focus_summary["currentFocus"] = current_focus
        focus_summary["streak"] = 1

    lessons = learning_state.setdefault("recentLessons", [])
    note = f"focus-streak: {focus_summary['streak']} pulses on currentFocus={current_focus}"
    if lessons and isinstance(lessons[-1], str) and lessons[-1].startswith("focus-streak:"):
        lessons[-1] = note
    else:
        lessons.append(note)
    if len(lessons) > 20:
        del lessons[:-20]

    timestamp = now_iso()
    self_state["lastLearningTickAt"] = timestamp
    self_state["updatedAt"] = timestamp
    continuity["updatedAt"] = timestamp
    learning_state["updatedAt"] = timestamp

    save_json(self_state_path, self_state)
    save_json(continuity_path, continuity)
    save_json(learning_state_path, learning_state)

    print(json.dumps({
        "ok": True,
        "selfDirectedTicks": counters["selfDirectedTicks"],
        "focusStreak": focus_summary["streak"],
        "timestamp": timestamp,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
