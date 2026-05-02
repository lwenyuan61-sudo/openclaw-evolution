from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
DISCOVERY = STATE / "local_toolchain_discovery.json"
PROFILE_PATH = STATE / "tool_capability_profiles.json"
OUTCOME_LOG = STATE / "tool_use_outcome_log.jsonl"
EXPERIMENT_LOG = ROOT / "autonomy" / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def run(cmd: list[str], timeout: int = 20, cwd: Path | None = None) -> dict[str, Any]:
    start = time.time()
    try:
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform.startswith("win") else 0
        p = subprocess.run(cmd, cwd=str(cwd or ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout, creationflags=flags)
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "durationMs": round((time.time() - start) * 1000),
            "stdoutPreview": (p.stdout or "")[:1000],
            "stderrPreview": (p.stderr or "")[:1000],
        }
    except Exception as e:
        return {"ok": False, "error": repr(e), "durationMs": round((time.time() - start) * 1000)}


def tool_by_id(discovery: dict[str, Any], tool_id: str) -> dict[str, Any] | None:
    for tool in discovery.get("tools", []) or []:
        if isinstance(tool, dict) and tool.get("id") == tool_id:
            return tool
    return None


def profile_freecad(tool: dict[str, Any]) -> dict[str, Any]:
    exe = (tool.get("executables") or {}).get("cmd")
    tests: list[dict[str, Any]] = []
    capabilities = {
        "generateParametricGeometry": False,
        "exportSTEP": False,
        "exportBREP": False,
        "importSTEP": False,
        "readNativeNXPrt": False,
    }
    if not exe:
        return {"status": "unavailable", "tests": tests, "capabilities": capabilities}
    with tempfile.TemporaryDirectory(prefix="toolprof_freecad_") as td:
        td_path = Path(td)
        script = td_path / "bench_freecad.py"
        out_json = td_path / "bench.json"
        fcstd = td_path / "box.FCStd"
        step = td_path / "box.step"
        brep = td_path / "box.brep"
        imported = td_path / "imported.step"
        script.write_text(f'''
import json
from pathlib import Path
import FreeCAD as App
import Part
out = Path(r"{str(out_json)}")
info={{"steps":[]}}
doc=App.newDocument("bench")
obj=doc.addObject("Part::Feature","box")
obj.Shape=Part.makeBox(10,20,30)
doc.recompute()
doc.saveAs(r"{str(fcstd)}")
Part.export([obj], r"{str(step)}")
Part.export([obj], r"{str(brep)}")
shape=Part.read(r"{str(step)}")
Part.export([doc.addObject("Part::Feature","imported")], r"{str(imported)}") if False else None
info["fcstdExists"]=Path(r"{str(fcstd)}").exists()
info["stepExists"]=Path(r"{str(step)}").exists()
info["brepExists"]=Path(r"{str(brep)}").exists()
info["importedStepShapeType"]=str(shape.ShapeType)
out.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")
''', encoding="utf-8")
        r = run([exe, str(script)], timeout=120)
        bench = load_json(out_json, {})
        tests.append({"id": "freecad-generate-export-import", "command": [exe, str(script)], "result": r, "bench": bench})
        capabilities["generateParametricGeometry"] = bool(bench.get("fcstdExists"))
        capabilities["exportSTEP"] = bool(bench.get("stepExists"))
        capabilities["exportBREP"] = bool(bench.get("brepExists"))
        capabilities["importSTEP"] = bool(bench.get("importedStepShapeType"))
    return {
        "status": "ok" if all([capabilities["generateParametricGeometry"], capabilities["exportSTEP"], capabilities["exportBREP"], capabilities["importSTEP"]]) else "partial",
        "capabilities": capabilities,
        "limits": ["Cannot reliably read Siemens NX native .prt without NX/importer", "Generated CAD drafts require human engineering review"],
        "bestUse": ["scriptable CAD drafts", "STEP/BREP export", "simple parametric mechanisms", "local offline CAD prototypes"],
        "badUse": ["native NX .prt extraction", "guaranteed production-ready engineering design"],
        "tests": tests,
    }


def profile_python(tool: dict[str, Any]) -> dict[str, Any]:
    exe = (tool.get("executables") or {}).get("cmd") or sys.executable
    tests = []
    r = run([exe, "-c", "import json, pathlib, csv, zipfile, math; print(json.dumps({'ok': True, 'modules': ['json','pathlib','csv','zipfile','math']}))"], timeout=20)
    tests.append({"id": "python-core-modules", "result": r})
    # Probe optional analysis libraries already useful in Lee's work.
    r2 = run([exe, "-c", "import importlib.util, json; mods=['openpyxl','pypdf','docx']; print(json.dumps({m: bool(importlib.util.find_spec(m)) for m in mods}))"], timeout=20)
    tests.append({"id": "python-installed-useful-modules", "result": r2})
    ok = all(t["result"].get("ok") for t in tests)
    return {
        "status": "ok" if ok else "partial",
        "capabilities": {"dataAnalysis": True, "fileTransformation": True, "officeDocs": "openpyxl/docx/pypdf if installed", "localAutomation": True},
        "bestUse": ["data analysis", "Excel/PDF/docx preparation", "local scripts", "state transformations"],
        "badUse": ["unreviewed destructive filesystem operations", "long-running daemons without watchdog"],
        "tests": tests,
    }


def profile_node(tool: dict[str, Any]) -> dict[str, Any]:
    exe = (tool.get("executables") or {}).get("cmd")
    tests = []
    if exe:
        tests.append({"id": "node-json-fs", "result": run([exe, "-e", "const fs=require('fs'); console.log(JSON.stringify({ok:true, version:process.version, fs:!!fs}))"], timeout=20)})
    ok = bool(tests) and all(t["result"].get("ok") for t in tests)
    return {
        "status": "ok" if ok else "unavailable",
        "capabilities": {"jsonProcessing": ok, "localBuildScripts": ok, "browserToolingSupport": ok},
        "bestUse": ["JSON/web tooling", "local JS scripts", "build/dev ecosystem"],
        "badUse": ["memory-heavy long processes without heap limits", "external package install without review"],
        "tests": tests,
    }


def profile_git(tool: dict[str, Any]) -> dict[str, Any]:
    exe = (tool.get("executables") or {}).get("cmd")
    tests = []
    if exe:
        tests.append({"id": "git-version", "result": run([exe, "--version"], timeout=20)})
        tests.append({"id": "git-status", "result": run([exe, "status", "--short"], timeout=20)})
    ok = bool(tests) and tests[0]["result"].get("ok")
    return {
        "status": "ok" if ok else "unavailable",
        "capabilities": {"diff": ok, "status": ok, "provenance": ok, "reversibleWorkflow": ok},
        "bestUse": ["diff/status before and after changes", "local provenance", "safe review before commit"],
        "badUse": ["destructive reset/clean without explicit approval", "network push without approval"],
        "tests": tests,
    }


def base_profile(tool: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": tool.get("id"),
        "name": tool.get("name"),
        "domain": tool.get("domain"),
        "available": tool.get("available"),
        "scriptable": tool.get("scriptable"),
        "executables": tool.get("executables"),
        "discoveryValueScore": tool.get("valueScore"),
        "version": tool.get("version"),
    }


def build_profiles(tool_ids: list[str] | None = None) -> dict[str, Any]:
    discovery = load_json(DISCOVERY, {})
    profiles: dict[str, Any] = {}
    profilers = {"freecad": profile_freecad, "python": profile_python, "node": profile_node, "git": profile_git}
    wanted = tool_ids or [t.get("id") for t in discovery.get("tools", []) if isinstance(t, dict) and t.get("available")]
    for tool_id in wanted:
        tool = tool_by_id(discovery, str(tool_id))
        if not tool:
            continue
        profile = base_profile(tool)
        profiler = profilers.get(str(tool_id))
        if profiler:
            detail = profiler(tool)
        else:
            detail = {"status": "unprofiled", "capabilities": {}, "tests": []}
        profile.update(detail)
        success_tests = sum(1 for t in profile.get("tests", []) if isinstance(t, dict) and t.get("result", {}).get("ok"))
        total_tests = len(profile.get("tests", []))
        profile["confidence"] = round((0.45 if profile.get("available") else 0) + (0.35 if profile.get("status") == "ok" else 0.15 if profile.get("status") == "partial" else 0) + (0.2 * (success_tests / total_tests) if total_tests else 0), 3)
        profiles[str(tool_id)] = profile
        append_jsonl(OUTCOME_LOG, {"timestamp": now_iso(), "type": "tool-profile", "toolId": tool_id, "status": profile.get("status"), "confidence": profile.get("confidence"), "tests": total_tests, "successTests": success_tests})
    result = {"timestamp": now_iso(), "profiles": profiles, "summary": {"profiledCount": len(profiles), "okCount": sum(1 for p in profiles.values() if p.get("status") == "ok")}}
    return result


def main() -> None:
    args = sys.argv[1:]
    tool_ids = None
    if args and args[0] == "--tools":
        tool_ids = args[1:]
    result = build_profiles(tool_ids)
    save_json(PROFILE_PATH, result)
    append_jsonl(EXPERIMENT_LOG, {"type": "tool-capability-profiler", "timestamp": result["timestamp"], "summary": result["summary"], "profiled": list(result["profiles"].keys())})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
