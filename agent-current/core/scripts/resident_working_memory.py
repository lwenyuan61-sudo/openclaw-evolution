from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
OUT = STATE / "resident_working_memory.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"_loadError": str(exc), "_path": str(path)}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tail(items, n: int):
    return list(items or [])[-n:]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(10.0, float(value))), 3)


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def signal_age_minutes(signal: dict) -> float | None:
    raw = signal.get("latestMtime") or signal.get("capturedAt") or signal.get("lastObservedAt")
    dt = parse_iso(raw)
    if not dt:
        return None
    return (datetime.now(timezone.utc).astimezone() - dt).total_seconds() / 60.0


def screen_control_plane_noise(signal: dict) -> dict:
    """Detect self-observation/control-plane screen churn before it dominates attention.

    Screen changes are real physical perception, so we keep them visible, but
    repeated OpenClaw/terminal/control-plane changes should be compressed below
    fresh Lee-facing evidence unless another signal proves user intent.
    """
    if signal.get("type") != "screen-changed":
        return {"matched": False}
    organ = signal.get("organEvidence", {}) if isinstance(signal.get("organEvidence"), dict) else {}
    labels = {str(item).lower() for item in (organ.get("semanticLabels") or [])}
    window = organ.get("activeWindow", {}) if isinstance(organ.get("activeWindow"), dict) else {}
    title = str(window.get("title") or "").lower()
    control_labels = {"assistant-control-plane", "development-or-agent-workspace"}
    control_title = any(marker in title for marker in ("openclaw control", "windows powershell", "powershell", "cmd.exe", "terminal"))
    repeat_count = int(signal.get("repeatCount", 0) or 0)
    matched = bool(labels & control_labels or control_title or repeat_count >= 12)
    return {
        "matched": matched,
        "labels": sorted(labels),
        "title": window.get("title"),
        "repeatCount": repeat_count,
        "reason": "control-plane-screen-churn" if matched else None,
    }


def score_signal(signal: dict) -> dict:
    signal_type = signal.get("type")
    provenance = signal.get("provenance")
    score = 1.0
    reasons = []
    age_minutes = signal_age_minutes(signal)
    control_plane = screen_control_plane_noise(signal)
    if signal_type == "screen-changed":
        score += 2.0; reasons.append("screen-change")
    if signal_type == "workspace-changed":
        score += 2.2; reasons.append("workspace-change")
    if provenance in {"user-change", "external"}:
        score += 2.5; reasons.append("external-or-user")
    if signal.get("artifactDiffAvailable"):
        score += 1.2; reasons.append("diff-available")
    if signal.get("artifactTextReadable"):
        score += 0.5; reasons.append("text-readable")
    if provenance in {"self-write", "self-sensed"}:
        score -= 1.8; reasons.append("self-origin")
    if control_plane.get("matched"):
        score -= 2.0; reasons.append("control-plane-compressed")
        if int(control_plane.get("repeatCount", 0) or 0) >= 12:
            score -= 1.0; reasons.append("repeated-screen-churn")
    if isinstance(age_minutes, (int, float)):
        if age_minutes > 1440:
            score -= 4.5; reasons.append("stale-over-1d")
        elif age_minutes > 180:
            score -= 2.5; reasons.append("stale-over-3h")
        elif age_minutes > 60:
            score -= 1.2; reasons.append("stale-over-1h")
    return {
        "kind": "signal",
        "id": signal.get("path") or signal.get("type") or "signal",
        "score": clamp_score(score),
        "reasons": reasons,
        "ageMinutes": round(age_minutes, 2) if isinstance(age_minutes, (int, float)) else None,
        "compression": control_plane if control_plane.get("matched") else None,
        "signal": signal,
    }


def score_task(task: dict) -> dict:
    score = 1.0
    reasons = []
    if task.get("status") == "attention-needed":
        score += 4.0; reasons.append("attention-needed")
    if task.get("phase") == "cooldown":
        remaining = task.get("cooldownRemainingMinutes")
        if isinstance(remaining, (int, float)) and remaining > 0:
            score -= min(3.0, remaining / 15.0); reasons.append("cooldown-active")
    if int(task.get("failureCount", 0) or 0) > 0:
        score += min(2.0, int(task.get("failureCount", 0)) * 0.5); reasons.append("has-failures")
    if int(task.get("repeatCount", 0) or 0) >= 3:
        score += 1.0; reasons.append("repeat-pattern")
    return {
        "kind": "task",
        "id": task.get("id"),
        "score": clamp_score(score),
        "reasons": reasons,
        "task": task,
    }


def action_distribution(intents: list[dict]) -> dict:
    counts = {}
    for item in intents:
        action = item.get("intent")
        if action:
            counts[action] = counts.get(action, 0) + 1
    total = sum(counts.values()) or 1
    dominant_action, dominant_count = max(counts.items(), key=lambda kv: kv[1]) if counts else (None, 0)
    return {
        "counts": counts,
        "total": total,
        "dominantAction": dominant_action,
        "dominantRatio": round(dominant_count / total, 3),
        "dominantCount": dominant_count,
    }


def build_priority_filter(latest_signals: list[dict], suppressed_signals: list[dict], tasks: list[dict], recent_intents: list[dict], reach_gate: dict, handoff: dict) -> dict:
    items = []
    for sig in latest_signals:
        items.append(score_signal(sig))
    for sig in suppressed_signals:
        scored = score_signal(sig)
        scored["score"] = clamp_score(scored["score"] - 1.5)
        scored["suppressed"] = True
        items.append(scored)
    for task in tasks[:12]:
        items.append(score_task(task))
    dist = action_distribution(recent_intents)
    if dist["dominantAction"] in {"continue-focus", "silent-wait"} and dist["dominantRatio"] >= 0.7 and dist["total"] >= 8:
        items.append({
            "kind": "pattern",
            "id": "dominant-low-value-action",
            "score": clamp_score(5.0 + dist["dominantRatio"] * 2.0),
            "reasons": ["recent-action-dominance", dist["dominantAction"]],
            "actionDistribution": dist,
            "suggestedAction": "diagnose-or-wait",
        })
    if handoff.get("pending"):
        items.append({"kind": "handoff", "id": "main-persona-handoff", "score": 9.0, "reasons": ["pending-handoff"]})
    must = reach_gate.get("mustRequirements") if isinstance(reach_gate, dict) else None
    if must:
        items.append({"kind": "gate", "id": "reachout-must-requirements", "score": 4.5, "reasons": list(must)[:5]})
    items = sorted(items, key=lambda item: item.get("score", 0), reverse=True)
    high = [item for item in items if item.get("score", 0) >= 7.0]
    medium = [item for item in items if 4.0 <= item.get("score", 0) < 7.0]
    low = [item for item in items if item.get("score", 0) < 4.0]
    return {
        "top": items[:8],
        "counts": {"high": len(high), "medium": len(medium), "low": len(low), "total": len(items)},
        "actionDistribution": dist,
        "recommendedAttention": "handoff" if any(item.get("kind") == "handoff" for item in high) else ("investigate" if high else ("watch" if medium else "compress")),
        "compression": {
            "keptTopItems": min(len(items), 8),
            "droppedLowItems": max(0, len(low) - 3),
            "principle": "Keep high/medium priority context explicit; compress low-priority self-origin maintenance noise.",
        },
    }

def task_snapshot(task_state: dict) -> list[dict]:
    tasks = task_state.get("tasks", {}) if isinstance(task_state.get("tasks"), dict) else {}
    result = []
    now = datetime.now(timezone.utc).astimezone()
    for task_id, task in tasks.items():
        if not isinstance(task, dict):
            continue
        cooldown_until = task.get("cooldownUntil")
        remaining = None
        if cooldown_until:
            try:
                dt = datetime.fromisoformat(cooldown_until)
                remaining = round((dt - now).total_seconds() / 60.0, 2)
            except Exception:
                remaining = None
        result.append({
            "id": task_id,
            "status": task.get("status"),
            "phase": task.get("phase"),
            "lastCompletedAt": task.get("lastCompletedAt"),
            "cooldownUntil": cooldown_until,
            "cooldownRemainingMinutes": remaining,
            "successCount": task.get("successCount", 0),
            "failureCount": task.get("failureCount", 0),
            "repeatCount": task.get("repeatCount", 0),
            "lastEvidenceFingerprint": task.get("lastEvidenceFingerprint"),
        })
    return sorted(result, key=lambda item: str(item.get("lastCompletedAt") or ""), reverse=True)


def main() -> None:
    self_state = load_optional_json(CORE / "self-state.json")
    continuity = load_optional_json(AUTO / "continuity-state.json")
    action_state = load_optional_json(CORE / "action-state.json")
    perception = load_optional_json(CORE / "perception-state.json")
    task_state = load_optional_json(STATE / "resident_task_state.json")
    opportunity = load_optional_json(STATE / "lee_opportunity_review.json")
    handoff = load_optional_json(STATE / "persona_deliberation_handoff.json")
    runtime = load_optional_json(STATE / "resident_runtime.json")

    recent_intents = tail(action_state.get("recentIntents", []), 10)
    recent_executions = tail(action_state.get("recentExecutions", []), 10)
    latest_signals = tail(perception.get("lastProbeSignals") or perception.get("recentSignals", []), 5)
    suppressed_signals = tail(perception.get("lastSuppressedSignals") or perception.get("recentSuppressedSignals", []), 5)
    tasks = task_snapshot(task_state)
    active_cooldowns = [item for item in tasks if isinstance(item.get("cooldownRemainingMinutes"), (int, float)) and item["cooldownRemainingMinutes"] > 0]
    reach_gate = opportunity.get("reachOutGate", {}) if isinstance(opportunity.get("reachOutGate"), dict) else {}
    priority_filter = build_priority_filter(latest_signals, suppressed_signals, tasks, recent_intents, reach_gate, handoff)
    waiting_on = []
    if active_cooldowns:
        waiting_on.append("task-cooldown")
    if reach_gate.get("mustRequirements"):
        waiting_on.extend(list(reach_gate.get("mustRequirements") or [])[:5])
    if handoff.get("pending"):
        waiting_on.append("main-persona-handoff")

    packet = {
        "timestamp": now_iso(),
        "purpose": "Short-term working memory for the resident cerebellum: current goal, recent actions, task phases, cooldowns, waiting conditions, and handoff state.",
        "current": {
            "focus": self_state.get("currentFocus"),
            "mode": self_state.get("currentMode") or continuity.get("currentMode"),
            "trackId": self_state.get("currentTrackId") or continuity.get("currentTrackId"),
            "lastAction": self_state.get("lastAction"),
            "nextStep": self_state.get("nextStep") or continuity.get("nextLikelyStep"),
            "residentPulseIndex": runtime.get("pulseIndex"),
            "residentTimestamp": runtime.get("timestamp"),
        },
        "recent": {
            "intents": recent_intents,
            "executionSummaries": [
                {
                    "timestamp": item.get("timestamp"),
                    "selectedAction": item.get("selectedAction"),
                    "status": item.get("status"),
                    "mode": item.get("mode"),
                    "summary": (item.get("review") or {}).get("summary") if isinstance(item.get("review"), dict) else None,
                }
                for item in recent_executions
            ],
        },
        "tasks": tasks,
        "activeCooldowns": active_cooldowns,
        "priorityFilter": priority_filter,
        "signals": {
            "latest": latest_signals,
            "suppressed": suppressed_signals,
        },
        "waitingOn": sorted(set(str(item) for item in waiting_on if item)),
        "handoff": {
            "pending": bool(handoff.get("pending")),
            "reason": handoff.get("reason"),
            "shouldReportToLee": bool(handoff.get("shouldReportToLee")),
        },
        "reachOutGate": {
            "decision": reach_gate.get("decision"),
            "shouldPrepare": reach_gate.get("shouldPrepare"),
            "shouldSurface": reach_gate.get("shouldSurface"),
            "missingEvidence": reach_gate.get("missingEvidence", []),
            "mustRequirements": reach_gate.get("mustRequirements", []),
        },
        "recommendedResidentPosture": (
            "handoff-ready" if priority_filter.get("recommendedAttention") == "handoff"
            else "investigate-priority" if priority_filter.get("recommendedAttention") == "investigate"
            else "cooldown-and-watch" if active_cooldowns
            else "observe-and-advance-smallest-safe-step"
        ),
        "policy": {
            "localOnly": True,
            "noExternalWrites": True,
            "mainPersonaOwnsJudgmentAndLeeContact": True,
        },
    }
    save_json(OUT, packet)
    print(json.dumps({"ok": True, "timestamp": packet["timestamp"], "output": str(OUT), "activeCooldownCount": len(active_cooldowns), "priorityAttention": priority_filter.get("recommendedAttention"), "waitingOn": packet["waitingOn"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
