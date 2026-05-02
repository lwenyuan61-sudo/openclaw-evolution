from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2


def list_devices(max_index: int = 5) -> list[dict]:
    devices = []
    for idx in range(max_index + 1):
        cap = cv2.VideoCapture(idx)
        opened = cap.isOpened()
        width = None
        height = None
        if opened:
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        if opened:
            devices.append({"index": idx, "opened": True, "width": width, "height": height})
    return devices


def capture(device: int, output: Path, width: int | None, height: int | None) -> dict:
    output.parent.mkdir(parents=True, exist_ok=True)
    cap = cv2.VideoCapture(device)
    if not cap.isOpened():
        cap.release()
        raise SystemExit(f"camera-open-failed:{device}")
    if width:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    if height:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    ok, frame = cap.read()
    actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    if not ok:
        raise SystemExit("camera-capture-failed")
    if not cv2.imwrite(str(output), frame):
        raise SystemExit(f"write-failed:{output}")
    return {
        "output": str(output.resolve()),
        "device": device,
        "width": actual_width,
        "height": actual_height,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    list_p = sub.add_parser("list")
    list_p.add_argument("--max-index", type=int, default=5)

    cap_p = sub.add_parser("capture")
    cap_p.add_argument("output")
    cap_p.add_argument("--device", type=int, default=0)
    cap_p.add_argument("--width", type=int)
    cap_p.add_argument("--height", type=int)

    args = parser.parse_args()

    if args.command == "list":
        print(json.dumps(list_devices(args.max_index), ensure_ascii=False, indent=2))
    elif args.command == "capture":
        result = capture(args.device, Path(args.output), args.width, args.height)
        print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
