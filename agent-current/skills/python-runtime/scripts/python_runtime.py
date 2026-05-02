#!/usr/bin/env python3
"""Auditable local Python runtime wrapper."""
from __future__ import annotations

import argparse
import csv
import importlib.util
import json
import math
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run(cmd: list[str], timeout: int, cwd: Path | None = None) -> dict[str, Any]:
    start = time.time()
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
        proc = subprocess.run(cmd, cwd=str(cwd or Path.cwd()), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "durationMs": round((time.time() - start) * 1000),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "returncode": None, "durationMs": round((time.time() - start) * 1000), "stdout": exc.stdout or "", "stderr": f"timeout after {timeout}s"}
    except Exception as exc:
        return {"ok": False, "returncode": None, "durationMs": round((time.time() - start) * 1000), "stdout": "", "stderr": repr(exc)}


def write_json(path: str | None, data: dict[str, Any]) -> None:
    if not path:
        return
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def probe(args: argparse.Namespace) -> int:
    useful = ["json", "csv", "pathlib", "sqlite3", "zipfile", "openpyxl", "pypdf", "docx", "PIL", "numpy", "pandas", "matplotlib"]
    modules = {name: bool(importlib.util.find_spec(name)) for name in useful}
    payload = {
        "timestamp": now_iso(),
        "pythonExecutable": sys.executable,
        "version": sys.version,
        "platform": sys.platform,
        "cwd": str(Path.cwd()),
        "modules": modules,
        "policy": {
            "destructiveScriptsRequireApproval": True,
            "longRunningNeedsTimeoutOrWatchdog": True,
            "packageInstallRequiresMainPersonaJudgment": True,
        },
    }
    write_json(args.write_json, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def smoke_test(args: argparse.Namespace) -> int:
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = [
        {"item": "alpha", "value": 1},
        {"item": "beta", "value": 2},
        {"item": "gamma", "value": 3},
    ]
    csv_path = out / "smoke_input.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["item", "value"])
        writer.writeheader(); writer.writerows(rows)
    total = sum(int(r["value"]) for r in rows)
    result = {
        "timestamp": now_iso(),
        "ok": True,
        "csv": str(csv_path),
        "json": str(out / "smoke_result.json"),
        "count": len(rows),
        "sum": total,
        "sqrtSum": math.sqrt(total),
    }
    Path(result["json"]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def run_script(args: argparse.Namespace) -> int:
    script = Path(args.script)
    if not script.exists():
        payload = {"timestamp": now_iso(), "ok": False, "error": f"script not found: {script}"}
        write_json(args.write_json, payload); print(json.dumps(payload, ensure_ascii=False, indent=2)); return 2
    result = run([sys.executable, str(script), *args.script_args], timeout=args.timeout, cwd=Path(args.cwd) if args.cwd else None)
    payload = {"timestamp": now_iso(), "script": str(script), "timeout": args.timeout, **result}
    write_json(args.write_json, payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Python runtime wrapper")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("probe")
    p.add_argument("--write-json")
    p.set_defaults(func=probe)

    p = sub.add_parser("smoke-test")
    p.add_argument("--out-dir", default="state/python_runtime/smoke_test")
    p.set_defaults(func=smoke_test)

    p = sub.add_parser("run-script")
    p.add_argument("script")
    p.add_argument("script_args", nargs=argparse.REMAINDER)
    p.add_argument("--timeout", type=int, default=120)
    p.add_argument("--cwd")
    p.add_argument("--write-json")
    p.set_defaults(func=run_script)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
