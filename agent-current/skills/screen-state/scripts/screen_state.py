from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import mss
from PIL import Image


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def capture_screen(output_image: Path | None = None, downsample: int = 8) -> dict:
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        shot = sct.grab(monitor)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        if output_image:
            output_image.parent.mkdir(parents=True, exist_ok=True)
            image.save(output_image)

        small = image.resize((max(1, image.width // downsample), max(1, image.height // downsample)))
        digest = hashlib.sha256(small.tobytes()).hexdigest()

        return {
            "capturedAt": now_iso(),
            "width": image.width,
            "height": image.height,
            "monitor": {
                "left": monitor["left"],
                "top": monitor["top"],
                "width": monitor["width"],
                "height": monitor["height"],
            },
            "downsample": downsample,
            "screenHash": digest,
            "imagePath": None if not output_image else str(output_image.resolve()),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-json")
    parser.add_argument("--save-image")
    parser.add_argument("--downsample", type=int, default=8)
    args = parser.parse_args()

    output_image = Path(args.save_image) if args.save_image else None
    data = capture_screen(output_image=output_image, downsample=args.downsample)

    if args.write_json:
        out = Path(args.write_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
