from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "state"
PROFILES = STATE / "tool_capability_profiles.json"
OUT = STATE / "task_tool_matcher.json"
LOG = STATE / "tool_use_outcome_log.jsonl"
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


def tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z][a-zA-Z0-9_+-]{1,}|[\u4e00-\u9fff]{2,}", text.lower()))


TASK_PATTERNS = {
    "cad_generation": {"keywords": {"cad", "step", "stl", "brep", "freecad", "建模", "模型", "滑动", "轴承", "草案", "geometry"}, "preferred": {"freecad": 1.0, "python": 0.25}},
    "nx_native_read": {"keywords": {"nx", "prt", "siemens", "ug", "parasolid", "原生", "读取"}, "preferred": {"freecad": -0.4, "python": 0.2}},
    "data_analysis": {"keywords": {"excel", "xlsx", "csv", "pdf", "analysis", "统计", "作业", "数据", "表格", "chart", "图表"}, "preferred": {"python": 1.0, "git": 0.15, "node": 0.1}},
    "web_json_tooling": {"keywords": {"json", "node", "网页", "html", "javascript", "前端", "build"}, "preferred": {"node": 1.0, "python": 0.4}},
    "version_control": {"keywords": {"git", "diff", "commit", "版本", "回滚", "status", "补丁"}, "preferred": {"git": 1.0, "python": 0.2}},
    "media_processing": {"keywords": {"video", "audio", "音频", "视频", "转码", "剪辑", "ffmpeg"}, "preferred": {"ffmpeg": 1.0, "python": 0.25}},
}


def infer_task(text: str) -> dict[str, Any]:
    toks = tokenize(text)
    scores = []
    for task, spec in TASK_PATTERNS.items():
        hit = toks & spec["keywords"]
        if hit:
            scores.append({"task": task, "score": len(hit) / max(1, len(spec["keywords"])), "hits": sorted(hit)})
    scores.sort(key=lambda x: x["score"], reverse=True)
    return {"primary": scores[0]["task"] if scores else "general", "matches": scores}


def match_tools(task_text: str) -> dict[str, Any]:
    data = load_json(PROFILES, {})
    profiles = data.get("profiles", {}) if isinstance(data.get("profiles"), dict) else {}
    inferred = infer_task(task_text)
    primary = inferred["primary"]
    prefs = TASK_PATTERNS.get(primary, {}).get("preferred", {})
    ranked = []
    for tool_id, profile in profiles.items():
        if not isinstance(profile, dict):
            continue
        score = 0.0
        reasons = []
        confidence = float(profile.get("confidence", 0.0) or 0.0)
        if profile.get("available"):
            score += 1.0; reasons.append("available")
        if profile.get("scriptable"):
            score += 0.6; reasons.append("scriptable")
        if profile.get("status") == "ok":
            score += 0.8; reasons.append("benchmarked-ok")
        elif profile.get("status") == "partial":
            score += 0.35; reasons.append("benchmarked-partial")
        pref = float(prefs.get(tool_id, 0.0) or 0.0)
        if pref:
            score += 2.2 * pref
            reasons.append(f"task-preference={pref}")
        score += confidence
        # Penalize known bad uses when task words overlap.
        task_low = task_text.lower()
        for bad in profile.get("badUse", []) or []:
            if "nx" in task_low and "nx" in str(bad).lower():
                score -= 1.2
                reasons.append("penalty-known-bad-use-nx")
        ranked.append({
            "toolId": tool_id,
            "name": profile.get("name"),
            "score": round(score, 3),
            "confidence": confidence,
            "status": profile.get("status"),
            "domain": profile.get("domain"),
            "reasons": reasons,
            "bestUse": profile.get("bestUse", [])[:4],
            "badUse": profile.get("badUse", [])[:3],
        })
    ranked.sort(key=lambda x: x["score"], reverse=True)
    no_suitable_reason = None
    recommendation = ranked[0] if ranked else None
    if primary == "nx_native_read":
        # Python can extract strings/metadata from NX .prt, but it is not a real
        # native geometry reader. FreeCAD is explicitly bad for native NX .prt.
        # Prefer an honest blocker over a misleading installed-tool match.
        no_suitable_reason = "No installed local tool is verified for Siemens NX native .prt geometry extraction. Use Siemens NX/NXOpen or a licensed translator/export STEP/Parasolid/JT. Python is only useful for metadata/string extraction."
        recommendation = None
    if recommendation and float(recommendation.get("score", 0.0) or 0.0) < 3.0:
        no_suitable_reason = no_suitable_reason or "No tool exceeded the suitability threshold for this task."
        recommendation = None
    result = {"timestamp": now_iso(), "taskText": task_text, "inferredTask": inferred, "rankedTools": ranked, "recommendation": recommendation, "noSuitableToolReason": no_suitable_reason}
    return result


def main() -> None:
    task_text = " ".join(sys.argv[1:]).strip() or "general local task"
    result = match_tools(task_text)
    save_json(OUT, result)
    append_jsonl(LOG, {"timestamp": result["timestamp"], "type": "task-tool-match", "taskText": task_text[:300], "primaryTask": result["inferredTask"]["primary"], "recommendedTool": (result.get("recommendation") or {}).get("toolId")})
    append_jsonl(EXPERIMENT_LOG, {"type": "task-tool-matcher", "timestamp": result["timestamp"], "primaryTask": result["inferredTask"]["primary"], "recommendedTool": (result.get("recommendation") or {}).get("toolId")})
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
