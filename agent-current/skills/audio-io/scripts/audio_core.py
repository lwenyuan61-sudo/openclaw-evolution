from __future__ import annotations

import wave
from pathlib import Path

import numpy as np
import pyttsx3
import sounddevice as sd
from faster_whisper import WhisperModel

_WHISPER_MODEL = None


def list_devices() -> list[dict]:
    devices = []
    for idx, dev in enumerate(sd.query_devices()):
        devices.append(
            {
                "index": idx,
                "name": dev["name"],
                "max_input_channels": dev["max_input_channels"],
                "max_output_channels": dev["max_output_channels"],
                "default_samplerate": dev["default_samplerate"],
            }
        )
    return devices


def record(output: Path, seconds: float, samplerate: int, channels: int, device: int | None) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    frames = int(seconds * samplerate)
    data = sd.rec(frames, samplerate=samplerate, channels=channels, dtype="int16", device=device)
    sd.wait()
    with wave.open(str(output), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(samplerate)
        wf.writeframes(data.tobytes())
    peak = int(np.abs(data).max()) if data.size else 0
    return {
        "output": str(output.resolve()),
        "seconds": seconds,
        "samplerate": samplerate,
        "channels": channels,
        "peak": peak,
        "device": device,
    }


def speak(text: str, voice_contains: str | None = None, rate: int | None = None, save_to: Path | None = None) -> dict:
    engine = pyttsx3.init()
    voices = engine.getProperty("voices")
    selected = None
    if voice_contains:
        needle = voice_contains.lower()
        for voice in voices:
            hay = f"{voice.id} {voice.name}".lower()
            if needle in hay:
                selected = voice
                break
    if selected:
        engine.setProperty("voice", selected.id)
    if rate:
        engine.setProperty("rate", rate)
    if save_to:
        save_to.parent.mkdir(parents=True, exist_ok=True)
        engine.save_to_file(text, str(save_to))
    else:
        engine.say(text)
    engine.runAndWait()
    return {
        "text": text,
        "voice": None if not selected else selected.name,
        "saved": None if not save_to else str(save_to.resolve()),
    }


def get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = WhisperModel("tiny", device="cpu", compute_type="int8")
    return _WHISPER_MODEL


def transcribe(path: Path, language: str | None = None) -> dict:
    model = get_whisper_model()
    segments, info = model.transcribe(str(path), language=language)
    text = "".join(segment.text for segment in segments).strip()
    return {
        "path": str(path.resolve()),
        "language": info.language,
        "language_probability": info.language_probability,
        "text": text,
    }
