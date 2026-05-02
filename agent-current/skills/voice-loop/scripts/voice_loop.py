from __future__ import annotations

import argparse
import json
from pathlib import Path

from audio_core import record, speak, transcribe

DEFAULT_REPLY = "我听到了，但这次没有识别出清晰内容。你可以再说一遍。"


def build_reply(text: str, mode: str, fallback: str) -> str:
    clean = text.strip()
    if not clean:
        return fallback
    if mode == "echo":
        return f"我听到你说：{clean}"
    if mode == "confirm":
        return f"收到，你刚才说的是：{clean}"
    return clean


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=4)
    parser.add_argument("--samplerate", type=int, default=16000)
    parser.add_argument("--channels", type=int, default=1)
    parser.add_argument("--device", type=int)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--reply-mode", choices=["echo", "confirm", "literal"], default="confirm")
    parser.add_argument("--reply-text", help="Used when --reply-mode literal")
    parser.add_argument("--fallback-reply", default=DEFAULT_REPLY)
    parser.add_argument("--voice-contains")
    parser.add_argument("--rate", type=int)
    parser.add_argument("--prefix", default="voice_loop")
    parser.add_argument("--output-dir", default="state")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    audio_path = out_dir / f"{args.prefix}.wav"

    rec = record(audio_path, args.seconds, args.samplerate, args.channels, args.device)
    tr = transcribe(audio_path, args.language)

    if args.reply_mode == "literal":
        reply = args.reply_text or args.fallback_reply
    else:
        reply = build_reply(tr.get("text", ""), args.reply_mode, args.fallback_reply)

    tts = speak(reply, voice_contains=args.voice_contains, rate=args.rate)

    result = {
        "record": rec,
        "transcribe": tr,
        "reply": reply,
        "tts": tts,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
