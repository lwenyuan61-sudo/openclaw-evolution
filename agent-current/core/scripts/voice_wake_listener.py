from __future__ import annotations

import argparse
import json
import math
import time
import wave
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
STATUS_PATH = STATE / "voice_wake_status.json"
EVENTS_PATH = STATE / "voice_wake_events.jsonl"
AUDIO_DIR = STATE / "voice_wake_audio"

_MODEL = None


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_model() -> WhisperModel:
    global _MODEL
    if _MODEL is None:
        # CPU/int8: avoids GPU/VRAM use. This is heavier than phone-grade keyword spotting,
        # so it should be a fallback until a true wake-word engine exists.
        _MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _MODEL


def write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def rms_int16(data: np.ndarray) -> float:
    if data.size == 0:
        return 0.0
    x = data.astype(np.float32)
    return float(math.sqrt(float(np.mean(x * x))))


def save_wav(path: Path, data: np.ndarray, samplerate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(data.astype(np.int16).tobytes())


def contains_wake(text: str, wake_words: list[str]) -> bool:
    compact = text.lower().replace(" ", "")
    aliases = [w.lower().replace(" ", "") for w in wake_words]
    return any(alias and alias in compact for alias in aliases)


def main() -> None:
    parser = argparse.ArgumentParser(description="CPU-only advisory voice wake listener. Requires explicit user start.")
    parser.add_argument("--device", type=int)
    parser.add_argument("--samplerate", type=int, default=16000)
    parser.add_argument("--chunk-seconds", type=float, default=1.2)
    parser.add_argument("--phrase-seconds", type=float, default=3.0)
    parser.add_argument("--energy-threshold", type=float, default=650.0)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--wake-word", action="append", default=["the agent", "小碗", "hey local-evolution-agent", "hi local-evolution-agent"])
    parser.add_argument("--once", action="store_true", help="Run one phrase check and exit")
    parser.add_argument("--max-seconds", type=float, default=0.0, help="Safety limit; 0 means no limit")
    args = parser.parse_args()

    started = time.time()
    status = {
        "timestamp": now_iso(),
        "status": "running",
        "mode": "cpu-whisper-fallback",
        "device": args.device,
        "samplerate": args.samplerate,
        "wakeWords": args.wake_word,
        "privacy": {
            "alwaysListeningRequiresExplicitStart": True,
            "storesOnlyTriggeredAudioByDefault": False,
            "writesEventsTo": str(EVENTS_PATH),
        },
        "resourcePolicy": {
            "gpuUsed": False,
            "model": "faster-whisper tiny cpu int8 fallback",
            "betterOption": "install/use true keyword spotter such as Porcupine/openWakeWord if approved",
        },
    }
    write_json(STATUS_PATH, status)

    phrase_frames = int(args.phrase_seconds * args.samplerate)
    chunk_frames = int(args.chunk_seconds * args.samplerate)
    try:
        while True:
            if args.max_seconds and time.time() - started > args.max_seconds:
                break
            chunk = sd.rec(chunk_frames, samplerate=args.samplerate, channels=1, dtype="int16", device=args.device)
            sd.wait()
            level = rms_int16(chunk)
            if level < args.energy_threshold and not args.once:
                write_json(STATUS_PATH, {**status, "timestamp": now_iso(), "status": "listening", "lastRms": round(level, 2)})
                continue

            phrase = sd.rec(phrase_frames, samplerate=args.samplerate, channels=1, dtype="int16", device=args.device)
            sd.wait()
            phrase_level = rms_int16(phrase)
            AUDIO_DIR.mkdir(parents=True, exist_ok=True)
            wav = AUDIO_DIR / f"wake_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
            save_wav(wav, phrase, args.samplerate)
            model = load_model()
            segments, info = model.transcribe(str(wav), language=args.language)
            text = "".join(seg.text for seg in segments).strip()
            hit = contains_wake(text, args.wake_word)
            event = {
                "timestamp": now_iso(),
                "hit": hit,
                "text": text,
                "language": info.language,
                "languageProbability": info.language_probability,
                "rms": round(phrase_level, 2),
                "audioPath": str(wav) if hit else None,
                "policy": "non-hit audio file may be deleted by future cleanup; no external send",
            }
            if not hit:
                try:
                    wav.unlink()
                except FileNotFoundError:
                    pass
                event["audioPath"] = None
            append_jsonl(EVENTS_PATH, event)
            write_json(STATUS_PATH, {**status, "timestamp": now_iso(), "status": "wake-detected" if hit else "no-wake", "lastEvent": event})
            print(json.dumps(event, ensure_ascii=False), flush=True)
            if args.once or hit:
                break
    finally:
        final = {**status, "timestamp": now_iso(), "status": "stopped"}
        write_json(STATUS_PATH, final)


if __name__ == "__main__":
    main()
