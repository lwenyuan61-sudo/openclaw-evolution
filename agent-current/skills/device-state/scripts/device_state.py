from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import cv2
import pyttsx3
import sounddevice as sd


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def list_cameras(max_index: int = 5) -> list[dict]:
    cameras = []
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx)
        opened = cap.isOpened()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) if opened else None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) if opened else None
        cap.release()
        if opened:
            cameras.append({"index": idx, "width": width, "height": height})
    return cameras


def list_audio_devices() -> dict:
    inputs = []
    outputs = []
    for idx, dev in enumerate(sd.query_devices()):
        item = {
            "index": idx,
            "name": dev["name"],
            "default_samplerate": dev["default_samplerate"],
            "max_input_channels": dev["max_input_channels"],
            "max_output_channels": dev["max_output_channels"],
        }
        if dev["max_input_channels"] > 0:
            inputs.append(item)
        if dev["max_output_channels"] > 0:
            outputs.append(item)
    return {"inputs": inputs, "outputs": outputs}


def list_voices() -> list[dict]:
    engine = pyttsx3.init()
    voices = []
    for voice in engine.getProperty("voices"):
        voices.append({"id": voice.id, "name": voice.name})
    return voices


def snapshot(max_camera_index: int = 5) -> dict:
    audio = list_audio_devices()
    cameras = list_cameras(max_camera_index)
    voices = list_voices()
    return {
        "capturedAt": now_iso(),
        "summary": {
            "cameraCount": len(cameras),
            "inputAudioDeviceCount": len(audio["inputs"]),
            "outputAudioDeviceCount": len(audio["outputs"]),
            "voiceCount": len(voices),
        },
        "cameras": cameras,
        "audio": audio,
        "voices": voices,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max-camera-index", type=int, default=5)
    parser.add_argument("--write-json")
    args = parser.parse_args()

    data = snapshot(args.max_camera_index)

    if args.write_json:
        out = Path(args.write_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
