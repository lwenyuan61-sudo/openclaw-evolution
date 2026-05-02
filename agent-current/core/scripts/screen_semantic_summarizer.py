from __future__ import annotations

import ctypes
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
AUTO = ROOT / "autonomy"
SCREEN_STATE = STATE / "screen_state.json"
PERCEPTION = CORE / "perception-state.json"
OUTPUT = STATE / "screen_semantic_summary.json"
OCR_PROBE = STATE / "screen_ocr_availability_probe.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def active_window() -> dict[str, Any]:
    if not sys.platform.startswith("win"):
        return {"available": False, "reason": "non-windows"}
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        length = user32.GetWindowTextLengthW(hwnd)
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        title = buff.value
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_name = None
        try:
            import psutil  # type: ignore
            process_name = psutil.Process(pid.value).name()
        except Exception:
            process_name = None
        return {"available": True, "hwnd": int(hwnd), "title": title, "pid": int(pid.value), "processName": process_name}
    except Exception as exc:
        return {"available": False, "reason": str(exc)[:160]}


def classify(title: str, process_name: str | None) -> dict[str, Any]:
    joined = f"{title} {process_name or ''}".lower()
    labels: list[str] = []
    if any(k in joined for k in ["whatsapp", "telegram", "signal", "discord", "wechat"]):
        labels.append("chat-surface")
    if any(k in joined for k in ["code", "cursor", "visual studio", "powershell", "terminal"]):
        labels.append("development-or-agent-workspace")
    if any(k in joined for k in ["chrome", "edge", "browser", "firefox"]):
        labels.append("browser")
    if any(k in joined for k in ["openclaw", "the agent", "agent"]):
        labels.append("assistant-control-plane")
    if not labels:
        labels.append("unknown-active-window")
    return {
        "labels": labels,
        "attentionHint": "watch" if labels == ["unknown-active-window"] else "context-available",
        "summary": "Active window/title context is available; this turns a raw screen hash into a lightweight semantic signal.",
    }


def image_metadata(path_value: str | None) -> dict[str, Any]:
    if not path_value:
        return {"available": False, "reason": "missing-image-path"}
    path = Path(path_value)
    if not path.is_absolute():
        path = ROOT / path
    exists = path.exists()
    result: dict[str, Any] = {"available": exists, "path": str(path)}
    if exists:
        result["sizeBytes"] = path.stat().st_size
        try:
            from PIL import Image  # type: ignore
            with Image.open(path) as img:
                result["width"], result["height"] = img.size
                result["mode"] = img.mode
        except Exception as exc:
            result["imageOpenError"] = str(exc)[:160]
    return result


def main() -> None:
    ts = now_iso()
    screen = load_json(SCREEN_STATE)
    perception = load_json(PERCEPTION)
    ocr_probe = load_json(OCR_PROBE)
    active = active_window()
    title = str(active.get("title") or "")
    process_name = active.get("processName") if isinstance(active.get("processName"), str) else None
    classification = classify(title, process_name)
    emitted = list(perception.get("lastProbeSignals", []) or [])
    suppressed = list(perception.get("lastSuppressedSignals", []) or [])
    screen_signals = [s for s in emitted + suppressed if isinstance(s, dict) and s.get("type") == "screen-changed"]
    packet = {
        "timestamp": ts,
        "status": "ok",
        "purpose": "Convert raw screen hash changes into a lightweight semantic state packet before any resident action decision.",
        "screenHash": screen.get("screenHash") or perception.get("lastScreenHash"),
        "capturedAt": screen.get("capturedAt") or perception.get("lastScreenCapturedAt"),
        "dimensions": {"width": screen.get("width"), "height": screen.get("height")},
        "activeWindow": active,
        "classification": classification,
        "image": image_metadata(screen.get("imagePath")),
        "recentScreenSignals": screen_signals[-5:],
        "semanticEvidence": {
            "hasActiveWindowTitle": bool(title),
            "hasImageArtifact": bool(screen.get("imagePath")),
            "hasRecentScreenSignal": bool(screen_signals),
            "ocrAvailable": bool(ocr_probe.get("ocrAvailable")),
            "ocrReason": ocr_probe.get("reason") or "availability-probe-not-run; active-window and screenshot artifact remain the first safe semantic layer",
            "ocrUsablePaths": ocr_probe.get("usablePaths", []),
            "ocrProbeTimestamp": ocr_probe.get("timestamp"),
            "ocrRecommendation": ocr_probe.get("recommendation"),
        },
        "policy": {
            "advisoryOnly": True,
            "readOnly": True,
            "noExternalWrite": True,
            "doesNotActOnScreen": True,
        },
    }
    save_json(OUTPUT, packet)
    append_jsonl(LOG_PATH, {
        "id": "screen-semantic-summary-" + ts,
        "timestamp": ts,
        "type": "screen-semantic-summary",
        "status": "ok",
        "screenHash": packet.get("screenHash"),
        "labels": classification.get("labels"),
    })
    print(json.dumps({"ok": True, "timestamp": ts, "screenHash": packet.get("screenHash"), "labels": classification.get("labels"), "output": str(OUTPUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
