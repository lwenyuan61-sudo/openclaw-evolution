from __future__ import annotations

import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
OUTPUT = STATE / "screen_ocr_availability_probe.json"
REPORT = STATE / "self_evolution_ocr_probe_report.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def module_available(name: str) -> dict[str, Any]:
    try:
        spec = importlib.util.find_spec(name)
        return {
            "available": spec is not None,
            "name": name,
            "origin": getattr(spec, "origin", None) if spec is not None else None,
            "probe": "importlib.util.find_spec (no import executed)",
        }
    except Exception as exc:
        return {"available": False, "name": name, "error": str(exc)[:240], "probe": "find_spec-error"}


def command_probe(executable: str, args: list[str] | None = None) -> dict[str, Any]:
    path = shutil.which(executable)
    result: dict[str, Any] = {"available": bool(path), "executable": executable, "path": path}
    if not path or not args:
        return result
    try:
        completed = subprocess.run(
            [path, *args],
            cwd=str(ROOT),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=3,
            check=False,
        )
        output = (completed.stdout or "").strip().splitlines()
        result.update({"returncode": completed.returncode, "versionOutput": output[:4]})
    except Exception as exc:
        result["versionError"] = str(exc)[:240]
    return result


def windows_ocr_probe() -> dict[str, Any]:
    is_windows = sys.platform.startswith("win")
    probes = {
        "winrt_windows_media_ocr": module_available("winrt.windows.media.ocr"),
        "windows_media_ocr": module_available("windows.media.ocr"),
        "win32com": module_available("win32com"),
    }
    available = bool(is_windows and (probes["winrt_windows_media_ocr"].get("available") or probes["windows_media_ocr"].get("available")))
    reason = "python-winrt-windows-media-ocr-binding-present" if available else "no-python-windows-media-ocr-binding-detected"
    return {
        "available": available,
        "reason": reason if is_windows else "non-windows-platform",
        "platformIsWindows": is_windows,
        "bindings": probes,
        "note": "This is an advisory binding check only; it does not capture screen content or invoke OCR.",
    }


def build_probe() -> dict[str, Any]:
    timestamp = now_iso()
    tesseract = command_probe("tesseract", ["--version"])
    python_modules = {
        name: module_available(name)
        for name in [
            "pytesseract",
            "PIL",
            "cv2",
            "easyocr",
            "paddleocr",
            "keras_ocr",
            "winrt",
        ]
    }
    windows_ocr = windows_ocr_probe()
    usable_paths: list[str] = []
    if tesseract.get("available") and python_modules["pytesseract"].get("available") and python_modules["PIL"].get("available"):
        usable_paths.append("pytesseract+tesseract+PIL")
    if windows_ocr.get("available") and python_modules["PIL"].get("available"):
        usable_paths.append("Windows.Media.Ocr binding + PIL image bridge")
    # Heavy OCR libraries are only noted as installed by module spec.  They are
    # not treated as preferred paths because importing/running them can load
    # ML frameworks or GPU backends.
    heavy_installed = [name for name in ["easyocr", "paddleocr", "keras_ocr"] if python_modules[name].get("available")]
    available = bool(usable_paths)
    if available:
        recommendation = "safe-to-add-optional-ocr-runner-behind-explicit-low-cost-gate"
        reason = "at-least-one-lightweight-local-ocr-path-detected"
    elif tesseract.get("available") and not python_modules["pytesseract"].get("available"):
        recommendation = "advisory-only; tesseract executable exists but Python bridge is missing"
        reason = "partial-tesseract-stack"
    elif python_modules["pytesseract"].get("available") and not tesseract.get("available"):
        recommendation = "advisory-only; pytesseract exists but tesseract executable is missing from PATH"
        reason = "partial-pytesseract-stack"
    elif windows_ocr.get("available") and not python_modules["PIL"].get("available"):
        recommendation = "advisory-only; Windows OCR binding exists but image bridge is missing"
        reason = "partial-windows-ocr-stack"
    else:
        recommendation = "keep-active-window-and-screenshot-metadata-path; do-not-spend-vram"
        reason = "no-lightweight-local-ocr-path-detected"
    return {
        "timestamp": timestamp,
        "status": "ok",
        "purpose": "Read-only availability probe for local screen OCR / deeper screen semantic options.",
        "platform": {"system": platform.system(), "release": platform.release(), "python": sys.version.split()[0]},
        "policy": {
            "advisoryOnly": True,
            "readOnlyProbe": True,
            "noExternalWrites": True,
            "noPaidApis": True,
            "noGpuOrLocalModelExecution": True,
            "heavyLibrariesNotImported": ["easyocr", "paddleocr", "keras_ocr"],
        },
        "ocrAvailable": available,
        "reason": reason,
        "usablePaths": usable_paths,
        "recommendation": recommendation,
        "providers": {
            "tesseractExecutable": tesseract,
            "windowsMediaOcr": windows_ocr,
            "pythonModules": python_modules,
            "heavyOcrLibrariesInstalledBySpecOnly": heavy_installed,
        },
        "nextSmallestConnector": (
            "If usablePaths is non-empty, add an opt-in OCR extraction script that consumes an existing screenshot artifact and writes a short text confidence packet. "
            "If empty, keep screen_semantic_summarizer on active-window/title metadata and surface the missing dependency reason only."
        ),
    }


def main() -> None:
    packet = build_probe()
    save_json(OUTPUT, packet)
    report = {
        "timestamp": packet["timestamp"],
        "status": "implemented-advisory-probe",
        "resourceMode": "cpu-static-read-only",
        "wrote": [str(OUTPUT.relative_to(ROOT)), str(REPORT.relative_to(ROOT))],
        "summary": {
            "ocrAvailable": packet.get("ocrAvailable"),
            "reason": packet.get("reason"),
            "usablePaths": packet.get("usablePaths"),
            "recommendation": packet.get("recommendation"),
        },
        "verification": {"pending": ["py_compile", "consistency_check"]},
    }
    save_json(REPORT, report)
    print(json.dumps({"ok": True, "output": str(OUTPUT), "report": str(REPORT), "ocrAvailable": packet.get("ocrAvailable"), "reason": packet.get("reason")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
