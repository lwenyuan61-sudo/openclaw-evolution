from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
OUT = STATE / "resident_lifecycle_review.json"


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


def action_distribution(intents: list[dict]) -> dict:
    counts: dict[str, int] = {}
    for item in intents:
        action = item.get("intent") or item.get("selectedAction")
        if action:
            counts[str(action)] = counts.get(str(action), 0) + 1
    total = sum(counts.values()) or 0
    dominant = None
    dominant_count = 0
    if counts:
        dominant, dominant_count = max(counts.items(), key=lambda kv: kv[1])
    return {
        "counts": counts,
        "total": total,
        "dominantAction": dominant,
        "dominantCount": dominant_count,
        "dominantRatio": round((dominant_count / total), 3) if total else 0.0,
    }


def active_cooldown_ids(working_memory: dict) -> set[str]:
    ids = set()
    for item in list(working_memory.get("activeCooldowns", []) or []):
        if isinstance(item, dict) and item.get("id"):
            ids.add(str(item.get("id")))
    return ids


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def cooldown_active(task: dict) -> bool:
    until = parse_iso(task.get("cooldownUntil"))
    return bool(until and datetime.now(timezone.utc).astimezone() < until)


def task_by_id(task_state: dict, task_id: str) -> dict:
    tasks = task_state.get("tasks", {}) if isinstance(task_state.get("tasks"), dict) else {}
    task = tasks.get(task_id, {})
    return task if isinstance(task, dict) else {}


def evaluate_proposal_outcome(proposal: dict, task_state: dict, dist: dict) -> dict:
    """Estimate whether repeating a lifecycle proposal is still useful.

    The review proposer is intentionally advisory, but without an outcome loop
    it can keep recommending the same safe verification action after it already
    completed.  This small evaluator uses resident_task_state plus the current
    action distribution to decay proposals that have not reduced a low-value
    continue/silent pattern, while allowing non-repeating proposals to recover.
    """
    action = str(proposal.get("action") or "")
    task = task_by_id(task_state, action)
    dominant_action = dist.get("dominantAction")
    dominant_ratio = float(dist.get("dominantRatio") or 0)
    low_value_still_dominant = dominant_action in {"continue-focus", "silent-wait"} and dominant_ratio >= 0.55
    repeat_count = int(task.get("repeatCount", 0) or 0)
    success_count = int(task.get("successCount", 0) or 0)
    failure_count = int(task.get("failureCount", 0) or 0)
    active = cooldown_active(task)

    multiplier = 1.0
    verdict = "neutral"
    reason = "no prior resident task outcome for this action"
    if task:
        verdict = "recoverable"
        reason = "prior outcome exists but current distribution does not show the old low-value dominance"
        if low_value_still_dominant and task.get("status") == "completed":
            verdict = "decay-repeat"
            reason = "same low-value distribution still dominates after this action completed"
            multiplier = 0.65
            if active:
                multiplier = 0.35
                reason += "; task cooldown is still active"
            if repeat_count >= 2:
                multiplier = min(multiplier, 0.4)
                reason += "; same-fingerprint repeats accumulated"
        elif not low_value_still_dominant and success_count > failure_count:
            verdict = "strengthen-if-needed"
            reason = "recent task history is successful and low-value dominance is not currently active"
            multiplier = 1.12

    adjusted_boost = round(float(proposal.get("boost", 0.0) or 0.0) * multiplier, 3)
    adjusted_confidence = round(max(0.05, min(0.99, float(proposal.get("confidence", 1.0) or 1.0) * (0.8 + multiplier * 0.2))), 3)
    return {
        "action": action,
        "verdict": verdict,
        "reason": reason,
        "multiplier": round(multiplier, 3),
        "adjustedBoost": adjusted_boost,
        "adjustedConfidence": adjusted_confidence,
        "taskStatus": task.get("status"),
        "repeatCount": repeat_count,
        "successCount": success_count,
        "failureCount": failure_count,
        "cooldownActive": active,
    }


def apply_outcome_evaluations(proposals: list[dict], task_state: dict, dist: dict) -> list[dict]:
    adjusted = []
    for proposal in proposals:
        item = dict(proposal)
        evaluation = evaluate_proposal_outcome(item, task_state, dist)
        item["outcomeEvaluation"] = evaluation
        item["boost"] = evaluation["adjustedBoost"]
        item["confidence"] = evaluation["adjustedConfidence"]
        adjusted.append(item)
    return adjusted


def propose_from_state(action_state: dict, task_state: dict, working_memory: dict) -> list[dict]:
    recent_intents = list(action_state.get("recentIntents", []) or [])[-16:]
    recent_executions = list(action_state.get("recentExecutions", []) or [])[-16:]
    dist = action_distribution(recent_intents)
    cooldowns = active_cooldown_ids(working_memory)
    priority = working_memory.get("priorityFilter", {}) if isinstance(working_memory.get("priorityFilter"), dict) else {}
    priority_attention = priority.get("recommendedAttention")
    top_priority = list(priority.get("top", []) or [])
    has_recent_screen_signal = any(
        isinstance(item, dict)
        and item.get("kind") == "signal"
        and (item.get("signal") or {}).get("type") == "screen-changed"
        and float(item.get("score", 0) or 0) >= 2.5
        for item in top_priority
    )
    proposals: list[dict] = []

    dominant_action = dist.get("dominantAction")
    dominant_ratio = float(dist.get("dominantRatio") or 0)
    total = int(dist.get("total") or 0)
    if dominant_action in {"continue-focus", "silent-wait"} and dominant_ratio >= 0.55 and total >= 8:
        proposal_id = f"break-{dominant_action}-dominance"
        continue_task = task_by_id(task_state, "continue-focus")
        silent_task = task_by_id(task_state, "silent-wait")
        confidence = min(0.95, 0.45 + dominant_ratio * 0.4 + min(total, 16) * 0.01)
        if has_recent_screen_signal and "inspect-local-signal" not in cooldowns:
            proposals.append({
                "id": proposal_id + "-inspect",
                "action": "inspect-local-signal",
                "phase": "diagnose",
                "boost": 6.0,
                "confidence": round(confidence, 3),
                "reason": "dominant low-value action pattern plus recent screen signal; do one bounded read-only diagnosis instead of continuing maintenance",
                "evidence": {"actionDistribution": dist, "priorityAttention": priority_attention, "hasRecentScreenSignal": True},
                "cooldownGuard": "do-not-repeat-if-inspect-local-signal-in-active-cooldown",
                "safe": "read-only-local",
            })
        elif "run-consistency-check" not in cooldowns:
            proposals.append({
                "id": proposal_id + "-verify",
                "action": "run-consistency-check",
                "phase": "verify",
                "boost": 15.0,
                "confidence": round(max(0.5, confidence - 0.15), 3),
                "reason": "dominant low-value action pattern without strong fresh signal; verify state health before more maintenance",
                "evidence": {
                    "actionDistribution": dist,
                    "continueSuccessCount": continue_task.get("successCount"),
                    "silentSuccessCount": silent_task.get("successCount"),
                },
                "safe": "read-only-local",
            })
        proposals.append({
            "id": proposal_id + "-cooldown-wait",
            "action": "silent-wait",
            "phase": "cooldown",
            "boost": 0.55,
            "confidence": round(max(0.45, confidence - 0.2), 3),
            "reason": "low-priority compression posture; waiting is preferable to another maintain tick when no fresh evidence exists",
            "evidence": {"actionDistribution": dist, "priorityAttention": priority_attention},
            "safe": "local-no-op",
        })

    # If an attention-needed task exists, propose a verification path without
    # directly mutating external state.
    tasks = task_state.get("tasks", {}) if isinstance(task_state.get("tasks"), dict) else {}
    attention_needed = [task for task in tasks.values() if isinstance(task, dict) and task.get("status") == "attention-needed"]
    if attention_needed and "run-consistency-check" not in cooldowns:
        proposals.append({
            "id": "attention-needed-task-verify",
            "action": "run-consistency-check",
            "phase": "verify",
            "boost": 2.0,
            "confidence": 0.8,
            "reason": "one or more resident tasks require attention; run bounded consistency verification",
            "evidence": {"taskIds": [task.get("id") for task in attention_needed[:5]]},
            "safe": "read-only-local",
        })

    proposals = apply_outcome_evaluations(proposals, task_state, dist)

    # Deduplicate by action/id while preserving order.
    deduped = []
    seen = set()
    for item in proposals:
        key = (item.get("id"), item.get("action"))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped[:6]


def main() -> None:
    action_state = load_optional_json(CORE / "action-state.json")
    task_state = load_optional_json(STATE / "resident_task_state.json")
    working_memory = load_optional_json(STATE / "resident_working_memory.json")
    proposals = propose_from_state(action_state, task_state, working_memory)
    packet = {
        "timestamp": now_iso(),
        "status": "ok",
        "purpose": "Review resident task lifecycle and propose bounded observe/diagnose/verify/cooldown actions when low-value maintain/wait patterns dominate.",
        "proposals": proposals,
        "proposalCount": len(proposals),
        "policy": {
            "advisoryOnly": True,
            "localOnly": True,
            "noExternalWrites": True,
            "mainPersonaOwnsJudgmentAndLeeContact": True,
        },
    }
    save_json(OUT, packet)
    print(json.dumps({"ok": True, "timestamp": packet["timestamp"], "proposalCount": len(proposals), "proposalActions": [item.get("action") for item in proposals], "output": str(OUT)}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
