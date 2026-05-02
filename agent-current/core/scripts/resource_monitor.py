from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
CORE_OUT = CORE / "resource-state.json"
STATE_OUT = STATE / "resource_monitor.json"
LOG_PATH = STATE / "resource_monitor_log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def run_nvidia_smi() -> tuple[bool, list[dict], str | None]:
    cmd = [
        "nvidia-smi",
        "--query-gpu=index,name,memory.total,memory.used,memory.free,utilization.gpu",
        "--format=csv,noheader,nounits",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
    except FileNotFoundError:
        return False, [], "nvidia-smi-not-found"
    except Exception as exc:
        return False, [], f"nvidia-smi-error:{type(exc).__name__}:{exc}"
    if proc.returncode != 0:
        return False, [], proc.stderr.strip() or f"nvidia-smi-returncode-{proc.returncode}"
    gpus = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 6:
            continue
        idx, name, total, used, free, util = parts[:6]
        try:
            total_i = int(float(total)); used_i = int(float(used)); free_i = int(float(free)); util_i = int(float(util))
        except ValueError:
            continue
        pressure = used_i / total_i if total_i else 0.0
        gpus.append({
            "index": int(idx),
            "name": name,
            "memoryTotalMiB": total_i,
            "memoryUsedMiB": used_i,
            "memoryFreeMiB": free_i,
            "memoryPressure": round(pressure, 4),
            "utilizationGpuPercent": util_i,
        })
    return True, gpus, None


def collect_memory() -> dict:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        mem = MEMORYSTATUSEX()
        mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))
        if not ok:
            return {"status": "unavailable", "error": "GlobalMemoryStatusEx-failed"}
        used = mem.ullTotalPhys - mem.ullAvailPhys
        return {
            "status": "ok",
            "totalMiB": round(mem.ullTotalPhys / 1024 / 1024),
            "usedMiB": round(used / 1024 / 1024),
            "availableMiB": round(mem.ullAvailPhys / 1024 / 1024),
            "pressure": round(used / mem.ullTotalPhys, 4) if mem.ullTotalPhys else None,
            "loadPercent": int(mem.dwMemoryLoad),
        }
    try:
        pages = os.sysconf("SC_PHYS_PAGES")
        page_size = os.sysconf("SC_PAGE_SIZE")
        total = int(pages * page_size)
    except Exception as exc:
        return {"status": "unavailable", "error": f"memory-probe-error:{type(exc).__name__}:{exc}"}
    return {
        "status": "partial",
        "totalMiB": round(total / 1024 / 1024),
        "usedMiB": None,
        "availableMiB": None,
        "pressure": None,
        "loadPercent": None,
    }


def collect_disks() -> list[dict]:
    roots: list[str] = []
    if os.name == "nt":
        for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            root = f"{letter}:\\"
            if os.path.exists(root):
                roots.append(root)
    else:
        roots.append("/")
    disks = []
    for root in roots:
        try:
            total, used, free = shutil.disk_usage(root)
        except Exception as exc:
            disks.append({"root": root, "status": "unavailable", "error": f"disk-usage-error:{type(exc).__name__}:{exc}"})
            continue
        disks.append({
            "root": root,
            "status": "ok",
            "totalMiB": round(total / 1024 / 1024),
            "usedMiB": round(used / 1024 / 1024),
            "freeMiB": round(free / 1024 / 1024),
            "pressure": round(used / total, 4) if total else None,
            "usedPercent": round((used / total) * 100, 1) if total else None,
            "isWorkspaceDrive": str(ROOT).lower().startswith(root.lower()) if os.name == "nt" else root == "/",
        })
    return disks


def classify(gpus: list[dict], warn: float, critical: float, min_free: int) -> dict:
    if not gpus:
        return {"level": "unknown", "gpuAccelerationAllowed": False, "reason": "no-gpu-data"}
    max_pressure = max(float(g.get("memoryPressure", 0.0) or 0.0) for g in gpus)
    min_free_seen = min(int(g.get("memoryFreeMiB", 0) or 0) for g in gpus)
    if max_pressure >= critical or min_free_seen < min_free:
        return {
            "level": "critical",
            "gpuAccelerationAllowed": False,
            "reason": "vram-critical-or-free-below-floor",
            "recommendedMode": "compress-or-offload",
        }
    if max_pressure >= warn:
        return {
            "level": "warning",
            "gpuAccelerationAllowed": False,
            "reason": "vram-warning-threshold",
            "recommendedMode": "avoid-new-gpu-work",
        }
    return {
        "level": "ok",
        "gpuAccelerationAllowed": True,
        "reason": "vram-headroom-ok",
        "recommendedMode": "local-cpu-first-gpu-allowed-if-needed",
    }


def classify_all(gpu_pressure: dict, memory: dict, disks: list[dict], args: argparse.Namespace) -> dict:
    reasons = []
    level = gpu_pressure.get("level", "unknown")
    gpu_allowed = bool(gpu_pressure.get("gpuAccelerationAllowed"))

    memory_pressure = memory.get("pressure")
    if isinstance(memory_pressure, (int, float)):
        if memory_pressure >= args.critical_memory_pressure:
            level = "critical"
            gpu_allowed = False
            reasons.append("memory-critical-threshold")
        elif memory_pressure >= args.warn_memory_pressure and level not in {"critical"}:
            level = "warning"
            reasons.append("memory-warning-threshold")

    ok_disks = [d for d in disks if d.get("status") == "ok"]
    workspace_disks = [d for d in ok_disks if d.get("isWorkspaceDrive")]
    disks_to_check = workspace_disks or ok_disks
    for disk in disks_to_check:
        free = int(disk.get("freeMiB", 0) or 0)
        pressure = disk.get("pressure")
        if free < args.critical_disk_free_mib or (isinstance(pressure, (int, float)) and pressure >= args.critical_disk_pressure):
            level = "critical"
            gpu_allowed = False
            reasons.append(f"disk-critical:{disk.get('root')}")
        elif free < args.warn_disk_free_mib or (isinstance(pressure, (int, float)) and pressure >= args.warn_disk_pressure):
            if level not in {"critical"}:
                level = "warning"
            reasons.append(f"disk-warning:{disk.get('root')}")

    if not reasons:
        reasons.append(gpu_pressure.get("reason", "resources-ok"))
    if level == "critical":
        recommended = "compress-or-offload-and-free-memory-or-disk"
    elif level == "warning":
        recommended = "avoid-heavy-work-and-prefer-small-local-cpu-tasks"
    else:
        recommended = "local-cpu-first-gpu-allowed-if-needed"
    return {
        "level": level,
        "gpuAccelerationAllowed": gpu_allowed,
        "reason": ";".join(reasons),
        "recommendedMode": recommended,
        "components": {
            "gpu": gpu_pressure,
            "memory": {
                "level": "critical" if isinstance(memory_pressure, (int, float)) and memory_pressure >= args.critical_memory_pressure else "warning" if isinstance(memory_pressure, (int, float)) and memory_pressure >= args.warn_memory_pressure else memory.get("status", "unknown"),
                "pressure": memory_pressure,
            },
            "disk": {
                "checkedRoots": [d.get("root") for d in disks_to_check],
                "minFreeMiB": min((int(d.get("freeMiB", 0) or 0) for d in disks_to_check), default=None),
            },
        },
    }


def save(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(obj: dict) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warn-pressure", type=float, default=0.72)
    parser.add_argument("--critical-pressure", type=float, default=0.88)
    parser.add_argument("--min-free-mib", type=int, default=1024)
    parser.add_argument("--warn-memory-pressure", type=float, default=0.82)
    parser.add_argument("--critical-memory-pressure", type=float, default=0.92)
    parser.add_argument("--warn-disk-pressure", type=float, default=0.90)
    parser.add_argument("--critical-disk-pressure", type=float, default=0.95)
    parser.add_argument("--warn-disk-free-mib", type=int, default=20 * 1024)
    parser.add_argument("--critical-disk-free-mib", type=int, default=10 * 1024)
    args = parser.parse_args()

    ok, gpus, error = run_nvidia_smi()
    gpu_pressure = classify(gpus, args.warn_pressure, args.critical_pressure, args.min_free_mib)
    memory = collect_memory()
    disks = collect_disks()
    pressure = classify_all(gpu_pressure, memory, disks, args)
    data = {
        "timestamp": now_iso(),
        "status": "ok" if ok else "unavailable",
        "error": error,
        "gpus": gpus,
        "memory": memory,
        "disks": disks,
        "policy": {
            "warnPressure": args.warn_pressure,
            "criticalPressure": args.critical_pressure,
            "minFreeMiB": args.min_free_mib,
            "warnMemoryPressure": args.warn_memory_pressure,
            "criticalMemoryPressure": args.critical_memory_pressure,
            "warnDiskPressure": args.warn_disk_pressure,
            "criticalDiskPressure": args.critical_disk_pressure,
            "warnDiskFreeMiB": args.warn_disk_free_mib,
            "criticalDiskFreeMiB": args.critical_disk_free_mib,
            "localFirst": True,
            "onWarning": "avoid spawning GPU-heavy/local-model jobs; prefer CPU/cloud/subagent or compressed state",
            "onCritical": "do not start GPU-heavy work; compress context/artifacts, free RAM/disk, and offload/queue work elsewhere",
        },
        "resourcePressure": pressure,
    }
    save(CORE_OUT, data)
    save(STATE_OUT, data)
    append_log(data)
    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
