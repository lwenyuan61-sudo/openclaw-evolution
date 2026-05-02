from __future__ import annotations

import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
OUT = STATE / "local_toolchain_discovery.json"
LOG = ROOT / "autonomy" / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def first_existing(paths: list[str]) -> str | None:
    for raw in paths:
        p = Path(raw).expanduser()
        if p.exists():
            return str(p)
    return None


def command_version(cmd: list[str], timeout: int = 8) -> dict[str, Any]:
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
        p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags)
        text = (p.stdout or p.stderr or "").strip().splitlines()
        return {"ok": p.returncode == 0, "returncode": p.returncode, "versionLine": text[0] if text else ""}
    except Exception as e:
        return {"ok": False, "error": repr(e)}


def discover() -> dict[str, Any]:
    home = Path.home()
    program_files = Path("C:/Program Files")
    local = home / "AppData" / "Local" / "Programs"

    specs: list[dict[str, Any]] = [
        {
            "id": "freecad",
            "name": "FreeCAD",
            "domain": "cad",
            "scriptable": True,
            "highValueReason": "local parametric CAD generation/export via FreeCADCmd",
            "executables": {
                "cmd": [
                    shutil.which("FreeCADCmd") or "",
                    str(local / "FreeCAD 1.1" / "bin" / "FreeCADCmd.exe"),
                    str(program_files / "FreeCAD 1.1" / "bin" / "FreeCADCmd.exe"),
                ],
                "gui": [
                    shutil.which("FreeCAD") or "",
                    str(local / "FreeCAD 1.1" / "bin" / "FreeCAD.exe"),
                    str(program_files / "FreeCAD 1.1" / "bin" / "FreeCAD.exe"),
                ],
            },
            "versionArgs": ["--version"],
            "registeredAbility": "freecad-automation",
        },
        {
            "id": "python",
            "name": "Python",
            "domain": "automation",
            "scriptable": True,
            "highValueReason": "general local automation, analysis, file transformation",
            "executables": {"cmd": [shutil.which("python") or "", shutil.which("python3") or ""]},
            "versionArgs": ["--version"],
            "registeredAbility": "python-local-runtime",
        },
        {
            "id": "node",
            "name": "Node.js",
            "domain": "automation",
            "scriptable": True,
            "highValueReason": "local JS tooling, browser/control infrastructure, build scripts",
            "executables": {"cmd": [shutil.which("node") or ""]},
            "versionArgs": ["--version"],
            "registeredAbility": "node-local-runtime",
        },
        {
            "id": "git",
            "name": "Git",
            "domain": "developer-tooling",
            "scriptable": True,
            "highValueReason": "version control, diff, provenance, reversible changes",
            "executables": {"cmd": [shutil.which("git") or ""]},
            "versionArgs": ["--version"],
            "registeredAbility": "git-toolchain",
        },
        {
            "id": "ffmpeg",
            "name": "FFmpeg",
            "domain": "media",
            "scriptable": True,
            "highValueReason": "local audio/video conversion, clipping, metadata extraction",
            "executables": {"cmd": [shutil.which("ffmpeg") or ""]},
            "versionArgs": ["-version"],
            "registeredAbility": "ffmpeg-media-toolchain",
        },
        {
            "id": "blender",
            "name": "Blender",
            "domain": "3d",
            "scriptable": True,
            "highValueReason": "scriptable 3D generation/rendering if installed",
            "executables": {"cmd": [shutil.which("blender") or "", str(program_files / "Blender Foundation" / "Blender 4.3" / "blender.exe"), str(program_files / "Blender Foundation" / "Blender 4.2" / "blender.exe")]},
            "versionArgs": ["--version"],
            "registeredAbility": "blender-automation",
        },
        {
            "id": "openscad",
            "name": "OpenSCAD",
            "domain": "cad",
            "scriptable": True,
            "highValueReason": "scriptable constructive-solid-geometry CAD if installed",
            "executables": {"cmd": [shutil.which("openscad") or "", str(program_files / "OpenSCAD" / "openscad.exe")]},
            "versionArgs": ["--version"],
            "registeredAbility": "openscad-automation",
        },
    ]

    tools = []
    for spec in specs:
        exes = {}
        available = False
        version = None
        for kind, paths in spec.get("executables", {}).items():
            found = first_existing([p for p in paths if p])
            exes[kind] = found
            available = available or bool(found)
        cmd = exes.get("cmd")
        if cmd and spec.get("versionArgs"):
            version = command_version([cmd, *spec["versionArgs"]])
        score = 0.0
        if available:
            score += 0.45
        if spec.get("scriptable"):
            score += 0.25
        if spec.get("domain") in {"cad", "developer-tooling", "automation"}:
            score += 0.15
        if cmd:
            score += 0.15
        tools.append({
            "id": spec["id"],
            "name": spec["name"],
            "domain": spec["domain"],
            "scriptable": spec["scriptable"],
            "available": available,
            "executables": exes,
            "version": version,
            "valueScore": round(score, 3),
            "highValueReason": spec["highValueReason"],
            "registeredAbility": spec["registeredAbility"],
        })

    registry_path = ROOT / "core" / "capability-registry.json"
    registered_ids: set[str] = set()
    if registry_path.exists():
        try:
            reg = json.loads(registry_path.read_text(encoding="utf-8"))
            registered_ids = {str(a.get("id")) for a in reg.get("abilities", []) if isinstance(a, dict)}
        except Exception:
            registered_ids = set()
    opportunities = []
    for tool in tools:
        if not tool["available"] or tool["valueScore"] < 0.7:
            continue
        if tool["registeredAbility"] not in registered_ids:
            opportunities.append({
                "id": f"wire-local-toolchain-{tool['id']}",
                "toolId": tool["id"],
                "title": f"Wire local {tool['name']} toolchain into capability registry",
                "reason": tool["highValueReason"],
                "nextConcreteStep": f"Create or update skill/toolchain wrapper and register ability {tool['registeredAbility']}.",
                "valueScore": tool["valueScore"],
            })

    result = {
        "timestamp": now_iso(),
        "purpose": "Discover installed local scriptable tools that can become capability/toolchain connectors.",
        "tools": tools,
        "opportunities": opportunities,
        "summary": {
            "availableCount": sum(1 for t in tools if t["available"]),
            "scriptableAvailableCount": sum(1 for t in tools if t["available"] and t["scriptable"]),
            "opportunityCount": len(opportunities),
        },
    }
    return result


def main() -> None:
    result = discover()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_jsonl(LOG, {"type": "local-toolchain-discovery", "timestamp": result["timestamp"], "summary": result["summary"], "opportunityIds": [o["id"] for o in result["opportunities"]]})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
