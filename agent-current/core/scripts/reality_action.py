from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
ACTION_STATE_PATH = CORE / "action-state.json"
DESKTOP_SCRIPT = ROOT / "skills" / "desktop-input" / "scripts" / "desktop_input.py"
KEYBOARD_SCRIPT = ROOT / "skills" / "desktop-input" / "scripts" / "keyboard_input.py"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def run_python(script: Path, *args: str) -> tuple[int, str, str]:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    return proc.returncode, proc.stdout, proc.stderr


def build_command(intent: str, args: argparse.Namespace) -> tuple[Path, list[str], bool]:
    safe_read_only = False
    if intent == "inspect-cursor":
        safe_read_only = True
        return DESKTOP_SCRIPT, ["pos"], safe_read_only
    if intent == "key":
        return KEYBOARD_SCRIPT, ["key", "--name", args.key_name], safe_read_only
    if intent == "hotkey":
        return KEYBOARD_SCRIPT, ["hotkey", "--keys", args.keys], safe_read_only
    if intent == "type":
        return KEYBOARD_SCRIPT, ["type", "--text", args.text], safe_read_only
    if intent == "move-click":
        return DESKTOP_SCRIPT, ["move-click", "--x", str(args.x), "--y", str(args.y)], safe_read_only
    raise SystemExit(f"unsupported-intent:{intent}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--intent", required=True, choices=["inspect-cursor", "key", "hotkey", "type", "move-click"])
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--note")
    parser.add_argument("--key-name")
    parser.add_argument("--keys")
    parser.add_argument("--text")
    parser.add_argument("--x", type=int)
    parser.add_argument("--y", type=int)
    args = parser.parse_args()

    action_state = load_json(ACTION_STATE_PATH)
    script, command_args, safe_read_only = build_command(args.intent, args)

    record = {
        "timestamp": now_iso(),
        "intent": args.intent,
        "execute": bool(args.execute),
        "safeReadOnly": safe_read_only,
        "note": args.note,
        "command": [str(script), *command_args],
    }

    action_state.setdefault("recentIntents", []).append(record)
    if len(action_state["recentIntents"]) > 50:
        del action_state["recentIntents"][:-50]

    if not args.execute and not safe_read_only:
        result = {"status": "dry-run", **record}
    else:
        rc, out, err = run_python(script, *command_args)
        result = {
            "status": "ok" if rc == 0 else "error",
            "returncode": rc,
            "stdout": out.strip(),
            "stderr": err.strip(),
            **record,
        }
        action_state.setdefault("recentExecutions", []).append(result)
        if len(action_state["recentExecutions"]) > 50:
            del action_state["recentExecutions"][:-50]

    action_state["updatedAt"] = now_iso()
    save_json(ACTION_STATE_PATH, action_state)
    append_jsonl(STATE / "reality_action_log.jsonl", result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
