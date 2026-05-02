from __future__ import annotations

import argparse
import json
from pathlib import Path

from audio_core import list_devices, record, speak, transcribe


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list")

    rec_p = sub.add_parser("record")
    rec_p.add_argument("output")
    rec_p.add_argument("--seconds", type=float, default=3)
    rec_p.add_argument("--samplerate", type=int, default=16000)
    rec_p.add_argument("--channels", type=int, default=1)
    rec_p.add_argument("--device", type=int)

    speak_p = sub.add_parser("speak")
    speak_p.add_argument("--text", required=True)
    speak_p.add_argument("--voice-contains")
    speak_p.add_argument("--rate", type=int)
    speak_p.add_argument("--save-to")

    tr_p = sub.add_parser("transcribe")
    tr_p.add_argument("path")
    tr_p.add_argument("--language")

    args = parser.parse_args()

    if args.command == "list":
        print(json.dumps(list_devices(), ensure_ascii=False, indent=2))
    elif args.command == "record":
        print(json.dumps(record(Path(args.output), args.seconds, args.samplerate, args.channels, args.device), ensure_ascii=False))
    elif args.command == "speak":
        save_to = Path(args.save_to) if args.save_to else None
        print(json.dumps(speak(args.text, args.voice_contains, args.rate, save_to), ensure_ascii=False))
    elif args.command == "transcribe":
        print(json.dumps(transcribe(Path(args.path), args.language), ensure_ascii=False))


if __name__ == "__main__":
    main()
