from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
OUT = STATE / "voice_calibration_status.json"
LEDGER = STATE / "voice_calibration_ledger.jsonl"
INDICATOR = STATE / "voice_listening_indicator.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def save(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def enumerate_devices() -> dict[str, Any]:
    try:
        import sounddevice as sd  # type: ignore

        devices = []
        for idx, item in enumerate(sd.query_devices()):
            devices.append(
                {
                    "index": idx,
                    "name": str(item.get("name")),
                    "maxInputChannels": int(item.get("max_input_channels", 0)),
                    "maxOutputChannels": int(item.get("max_output_channels", 0)),
                    "defaultSamplerate": float(item.get("default_samplerate", 0.0)),
                }
            )
        defaults = sd.default.device
        try:
            default_device = [int(x) if x is not None else None for x in defaults]
        except Exception:
            default_device = str(defaults)
        return {"ok": True, "devices": devices, "defaultDevice": default_device}
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}", "devices": [], "defaultDevice": None}


def pick_recommended_input(devices: list[dict[str, Any]]) -> dict[str, Any] | None:
    inputs = [d for d in devices if int(d.get("maxInputChannels") or 0) > 0]
    if not inputs:
        return None
    preferred = [d for d in inputs if "麦克风阵列" in str(d.get("name")) or "Mic Array" in str(d.get("name"))]
    return (preferred or inputs)[0]


def build_status() -> dict[str, Any]:
    ts = now_iso()
    enum = enumerate_devices()
    devices = enum.get("devices", []) if isinstance(enum.get("devices"), list) else []
    rec_input = pick_recommended_input(devices)
    input_count = sum(1 for d in devices if int(d.get("maxInputChannels") or 0) > 0)
    output_count = sum(1 for d in devices if int(d.get("maxOutputChannels") or 0) > 0)
    return {
        "timestamp": ts,
        "status": "ready" if enum.get("ok") and rec_input else "blocked-no-input-device",
        "mode": "manual-calibration-only",
        "alwaysOnMicEnabled": False,
        "recordingNow": False,
        "deviceEnumeration": {
            "ok": enum.get("ok"),
            "error": enum.get("error"),
            "defaultDevice": enum.get("defaultDevice"),
            "inputCount": input_count,
            "outputCount": output_count,
            "recommendedInput": rec_input,
        },
        "manualCalibrationPlan": {
            "durationSeconds": 3,
            "language": "zh",
            "steps": [
                "Show visible listening indicator before capture starts.",
                "Record a short 3-second sample only after manual start.",
                "Measure peak/energy and optionally transcribe locally with faster-whisper tiny CPU.",
                "Write metadata ledger: time, duration, device index, peak, transcript availability; do not store private audio by default.",
                "Delete raw audio immediately after calibration unless Lee explicitly chooses to save samples.",
                "Turn listening indicator off and write final status."
            ],
            "samplePathIfApproved": "state/voice_calibration_sample.wav",
            "rawAudioDefaultRetention": "delete-after-local-analysis",
            "networkUpload": False,
            "paidApi": False,
            "gpuRequired": False,
        },
        "privacyLedger": {
            "path": str(LEDGER.relative_to(ROOT)),
            "recordsRawAudio": False,
            "recordsMetadata": True,
            "metadataFields": ["timestamp", "durationSeconds", "deviceIndex", "peak", "transcriptStatus", "rawAudioDeleted"],
        },
        "indicator": {
            "path": str(INDICATOR.relative_to(ROOT)),
            "visibleStateContract": {
                "idle": "not recording/listening",
                "manual-recording": "short calibration capture in progress",
                "error": "capture failed; microphone must be idle/off afterwards",
            },
        },
        "blockedModes": {
            "always-on-listener": "blocked until separate explicit always-on approval and visible app control",
            "background-capture": "blocked; manual calibration only",
            "external-transcription": "blocked; local-only baseline",
        },
    }


def write_indicator(state: str, reason: str) -> None:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare/manual-preview voice calibration. Does not record audio unless a future explicit record mode is added.")
    parser.add_argument("--preview", action="store_true", help="Write a preview ledger entry without recording audio")
    args = parser.parse_args()
    status = build_status()
    save(OUT, status)
    write_indicator("idle", "manual calibration prepared; no audio capture started")
    event = {
        "timestamp": now_iso(),
        "event": "manual-calibration-schema-generated" if not args.preview else "manual-calibration-preview",
        "recordingStarted": False,
        "alwaysOnMicEnabled": False,
        "rawAudioCreated": False,
        "rawAudioDeleted": None,
        "status": status.get("status"),
    }
    append(LEDGER, event)
    print(json.dumps({"ok": status.get("status") == "ready", "out": str(OUT), "ledger": str(LEDGER), "indicator": str(INDICATOR), "event": event}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
