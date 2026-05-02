from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
AUDIO_SKILL = ROOT / "skills" / "audio-io" / "scripts"
if str(AUDIO_SKILL) not in sys.path:
    sys.path.insert(0, str(AUDIO_SKILL))

STATUS_PATH = STATE / "voice_calibration_status.json"
RUNNER_STATUS = STATE / "voice_manual_calibration_runner_status.json"
LEDGER = STATE / "voice_calibration_ledger.jsonl"
INDICATOR = STATE / "voice_listening_indicator.json"
DEFAULT_SAMPLE = STATE / "voice_calibration_sample.wav"
CONFIRM_TOKEN = "LEE_APPROVED_3_SECOND_LOCAL_CALIBRATION"


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


def set_indicator(state: str, reason: str) -> None:
    save(
        INDICATOR,
        {
            "timestamp": now_iso(),
            "state": state,
            "reason": reason,
            "recordingNow": state == "manual-recording",
            "alwaysOnMicEnabled": False,
        },
    )


def write_event(event: dict[str, Any]) -> dict[str, Any]:
    event.setdefault("timestamp", now_iso())
    event.setdefault("alwaysOnMicEnabled", False)
    event.setdefault("externalUpload", False)
    event.setdefault("paidApi", False)
    save(RUNNER_STATUS, event)
    append(LEDGER, event)
    return event


def recommended_input(status: dict[str, Any]) -> int | None:
    enum = status.get("deviceEnumeration", {}) if isinstance(status.get("deviceEnumeration"), dict) else {}
    rec = enum.get("recommendedInput", {}) if isinstance(enum.get("recommendedInput"), dict) else {}
    idx = rec.get("index")
    return int(idx) if isinstance(idx, int) else None


def preview(args: argparse.Namespace) -> dict[str, Any]:
    status = load(STATUS_PATH, {})
    device = args.device if args.device is not None else recommended_input(status)
    set_indicator("idle", "manual calibration runner preview; no audio capture started")
    return write_event(
        {
            "event": "manual-calibration-runner-preview",
            "status": "previewed",
            "recordingStarted": False,
            "rawAudioCreated": False,
            "rawAudioDeleted": None,
            "durationSeconds": args.seconds,
            "deviceIndex": device,
            "samplePath": str((Path(args.output) if args.output else DEFAULT_SAMPLE).resolve()),
            "requiresConfirmTokenForRecord": CONFIRM_TOKEN,
            "wouldTranscribeLocally": bool(args.transcribe),
        }
    )


def run_record(args: argparse.Namespace) -> dict[str, Any]:
    if args.confirm != CONFIRM_TOKEN:
        set_indicator("idle", "manual calibration record blocked: missing confirmation token")
        return write_event(
            {
                "event": "manual-calibration-record-blocked",
                "status": "blocked",
                "reason": "missing-confirmation-token",
                "recordingStarted": False,
                "rawAudioCreated": False,
                "rawAudioDeleted": None,
                "requiredConfirmToken": CONFIRM_TOKEN,
            }
        )
    if args.seconds <= 0 or args.seconds > 5:
        set_indicator("idle", "manual calibration record blocked: invalid duration")
        return write_event(
            {
                "event": "manual-calibration-record-blocked",
                "status": "blocked",
                "reason": "duration-must-be-0-to-5-seconds",
                "recordingStarted": False,
                "rawAudioCreated": False,
                "rawAudioDeleted": None,
                "durationSeconds": args.seconds,
            }
        )

    from audio_core import record, transcribe  # type: ignore

    status = load(STATUS_PATH, {})
    device = args.device if args.device is not None else recommended_input(status)
    sample = Path(args.output) if args.output else DEFAULT_SAMPLE
    set_indicator("manual-recording", "manual calibration capture in progress")
    raw_created = False
    raw_deleted = False
    transcript: dict[str, Any] | None = None
    try:
        rec = record(sample, args.seconds, args.samplerate, args.channels, device)
        raw_created = True
        if args.transcribe:
            transcript = transcribe(sample, args.language)
        if not args.keep_raw and sample.exists():
            sample.unlink()
            raw_deleted = True
        event = {
            "event": "manual-calibration-recorded",
            "status": "completed",
            "recordingStarted": True,
            "durationSeconds": args.seconds,
            "deviceIndex": device,
            "peak": rec.get("peak"),
            "samplerate": args.samplerate,
            "channels": args.channels,
            "rawAudioCreated": raw_created,
            "rawAudioDeleted": raw_deleted,
            "rawAudioKept": bool(args.keep_raw),
            "transcriptStatus": "completed" if transcript else "skipped",
            "transcriptText": None if not transcript else transcript.get("text"),
            "transcriptLanguage": None if not transcript else transcript.get("language"),
        }
        return write_event(event)
    except Exception as exc:
        return write_event(
            {
                "event": "manual-calibration-record-error",
                "status": "error",
                "recordingStarted": True,
                "rawAudioCreated": raw_created,
                "rawAudioDeleted": raw_deleted,
                "error": f"{type(exc).__name__}: {exc}",
            }
        )
    finally:
        set_indicator("idle", "manual calibration finished or stopped; microphone idle")


def main() -> None:
    parser = argparse.ArgumentParser(description="One-shot manual voice calibration runner. Default is preview only; recording requires an explicit confirmation token.")
    parser.add_argument("--record", action="store_true", help="Record one short manual calibration sample. Requires --confirm token.")
    parser.add_argument("--confirm", help=f"Required token for recording: {CONFIRM_TOKEN}")
    parser.add_argument("--seconds", type=float, default=3.0)
    parser.add_argument("--samplerate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--device", type=int)
    parser.add_argument("--output")
    parser.add_argument("--keep-raw", action="store_true", help="Keep raw WAV instead of deleting after local analysis.")
    parser.add_argument("--transcribe", action="store_true", help="Transcribe locally with faster-whisper tiny CPU after recording.")
    parser.add_argument("--language", default="zh")
    args = parser.parse_args()

    result = run_record(args) if args.record else preview(args)
    print(json.dumps({"ok": result.get("status") in {"previewed", "completed"}, "result": result, "statusPath": str(RUNNER_STATUS)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
