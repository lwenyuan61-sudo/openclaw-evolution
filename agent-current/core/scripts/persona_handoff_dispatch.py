from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
HANDOFF_PATH = STATE / "persona_deliberation_handoff.json"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def minutes_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return (now() - dt).total_seconds() / 60.0


def build_event_text(handoff: dict, claim_state: str) -> str:
    question = handoff.get("question") or "有一个需要the agent本人格继续接手的内部问题"
    track_id = handoff.get("currentTrackId") or "unknown-track"
    reason = handoff.get("reason") or "persona-handoff-pending"
    summary = handoff.get("summary") or "脚本层已经完成初步 triage，需要the agent本人格在完整连续性上下文里继续处理。"
    report_hint = ""
    if handoff.get("shouldReportToLee") or (isinstance(handoff.get("leeReportRecommendation"), dict) and handoff.get("leeReportRecommendation", {}).get("shouldReportToLee")):
        report_hint = " 这次接手若完成最小核实，应在同一次 wake 中直接向 Lee 汇报有价值的思考结果。"
    claim_hint = "请先运行 core/scripts/persona_handoff_claim.py，再继续处理并在完成后运行 core/scripts/persona_handoff_complete.py。"
    if claim_state == "stale-claimed":
        claim_hint = "这个 handoff 之前有 claim 但已 stale；请重新 claim 后继续处理，并在完成后运行 core/scripts/persona_handoff_complete.py。"
    delivery_hint = (
        "注意：resident/subagent 只能请求或准备汇报；真正 report 必须由 main persona 在当前 owner chat "
        "发出可见消息。只有确认可见消息会被发送时，才可使用 persona_handoff_complete.py "
        "--reported-to-lee --visible-delivery-confirmed；否则不要把 reportedToLee 标为 true。"
    )
    return (
        "Persona handoff pending. 这不是无上下文的新任务，而是the agent本人格对当前主线的续篇。 "
        f"track={track_id}; reason={reason}; claimState={claim_state}. "
        f"question={question}. summary={summary}{report_hint} "
        "请立即读取 state/persona_deliberation_handoff.json 以及其中列出的 contextFiles，"
        f"{claim_hint} {delivery_hint}"
    )


def run_system_event(text: str, mode: str, timeout_ms: int) -> tuple[int, str, str]:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    openclaw_bin = shutil.which("openclaw.cmd") or shutil.which("openclaw")
    if not openclaw_bin:
        raise FileNotFoundError("openclaw executable not found in PATH")
    proc = subprocess.run(
        [
            openclaw_bin,
            "system",
            "event",
            "--json",
            "--mode",
            mode,
            "--timeout",
            str(timeout_ms),
            "--text",
            text,
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default="now", choices=["now", "next-heartbeat"])
    parser.add_argument("--timeout-ms", type=int, default=15000)
    parser.add_argument("--dedupe-minutes", type=float, default=5.0)
    parser.add_argument("--claim-stale-minutes", type=float, default=20.0)
    args = parser.parse_args()

    handoff = load_optional_json(HANDOFF_PATH)
    if not handoff.get("pending"):
        result = {
            "status": "skipped",
            "reason": "no-pending-persona-handoff",
            "timestamp": now_iso(),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    if handoff.get("handledAt"):
        result = {
            "status": "skipped",
            "reason": "handoff-already-handled",
            "timestamp": now_iso(),
            "handledAt": handoff.get("handledAt"),
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    claimed_at = handoff.get("claimedAt")
    claim_elapsed = minutes_since(claimed_at)
    claim_id = handoff.get("claimId")
    claim_state = "unclaimed"
    if claim_id and claimed_at:
        if claim_elapsed is None or claim_elapsed < float(args.claim_stale_minutes):
            claim_state = "active-claimed"
        else:
            claim_state = "stale-claimed"

    if claim_state == "active-claimed":
        result = {
            "status": "skipped",
            "reason": "handoff-claimed-in-progress",
            "timestamp": now_iso(),
            "claimId": claim_id,
            "claimedAt": claimed_at,
            "claimedBy": handoff.get("claimedBy"),
            "elapsedMinutes": round(claim_elapsed, 3) if claim_elapsed is not None else None,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    last_wake_at = handoff.get("wakeRequestedAt")
    elapsed = minutes_since(last_wake_at)
    if elapsed is not None and elapsed < float(args.dedupe_minutes):
        result = {
            "status": "skipped",
            "reason": "wake-request-deduped",
            "timestamp": now_iso(),
            "wakeRequestedAt": last_wake_at,
            "elapsedMinutes": round(elapsed, 3),
            "claimState": claim_state,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    event_text = build_event_text(handoff, claim_state)
    rc, stdout, stderr = run_system_event(event_text, args.mode, args.timeout_ms)
    parsed = None
    if stdout:
        try:
            parsed = json.loads(stdout)
        except Exception:
            parsed = None

    timestamp = now_iso()
    handoff["wakeRequestedAt"] = timestamp
    handoff["wakeRequestCount"] = int(handoff.get("wakeRequestCount", 0) or 0) + 1
    handoff["lastWakeMode"] = args.mode
    handoff["lastWakeEventText"] = event_text
    handoff["lastWakeResult"] = {
        "returncode": rc,
        "stdout": parsed or stdout,
        "stderr": stderr,
        "timestamp": timestamp,
        "claimState": claim_state,
    }
    save_json(HANDOFF_PATH, handoff)

    result = {
        "status": "ok" if rc == 0 else "warning",
        "timestamp": timestamp,
        "mode": args.mode,
        "claimState": claim_state,
        "wakeRequestCount": handoff.get("wakeRequestCount"),
        "returncode": rc,
        "stdout": parsed or stdout,
        "stderr": stderr,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
