from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEARNING_STATE = ROOT / "core" / "learning-state.json"
PROCEDURAL_MEMORY = ROOT / "core" / "procedural-memory.json"

DEFAULT_MIN = 0.05
DEFAULT_MAX = 3.0
DEFAULT_STEP = 0.08
DEFAULT_HABIT_CONFIDENCE = 1.0
DEFAULT_HABIT_BOOST = 0.65


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp(value: float, lo: float = DEFAULT_MIN, hi: float = DEFAULT_MAX) -> float:
    return max(lo, min(hi, value))


def clamp_unit(value: float, lo: float = 0.2, hi: float = 1.8) -> float:
    return max(lo, min(hi, value))


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def minutes_since(value: str | None) -> float | None:
    dt = parse_iso(value)
    if not dt:
        return None
    return (datetime.now(timezone.utc).astimezone() - dt).total_seconds() / 60.0


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []
    parts = [item.strip() for item in value.split(",")]
    return [item for item in parts if item]


def canonicalize_value(value):
    if isinstance(value, list):
        return sorted({item for item in value if item})
    return value


def canonicalize_conditions(conditions: dict) -> dict:
    return {key: canonicalize_value(value) for key, value in sorted((conditions or {}).items())}


def build_conditions(args: argparse.Namespace) -> dict:
    conditions: dict[str, object] = {}
    if args.requires_current_focus:
        conditions["requiresCurrentFocus"] = True
    if args.requires_no_signals:
        conditions["requiresNoSignals"] = True

    mappings = {
        "signalTypesAllIn": parse_csv(args.signal_types_all_in),
        "signalTypesAnyOf": parse_csv(args.signal_types_any_of),
        "signalTypesNoneOf": parse_csv(args.signal_types_none_of),
        "signalProvenanceAllIn": parse_csv(args.signal_provenance_all_in),
        "signalProvenanceAnyOf": parse_csv(args.signal_provenance_any_of),
        "signalProvenanceNoneOf": parse_csv(args.signal_provenance_none_of),
    }
    for key, value in mappings.items():
        if value:
            conditions[key] = sorted(set(value))
    return canonicalize_conditions(conditions)


def make_signature(event: str, action: str, conditions: dict) -> dict:
    return {
        "event": event,
        "action": action,
        "conditions": canonicalize_conditions(conditions),
    }


def make_signature_key(signature: dict) -> str:
    return json.dumps(signature, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return cleaned or "habit"


def same_conditions(a: dict, b: dict) -> bool:
    return canonicalize_conditions(a) == canonicalize_conditions(b)


def condition_pairs(conditions: dict) -> set[tuple[str, str]]:
    result: set[tuple[str, str]] = set()
    for key, value in canonicalize_conditions(conditions).items():
        if isinstance(value, list):
            for item in value:
                result.add((key, str(item)))
        else:
            result.add((key, str(value)))
    return result


def is_subset_conditions(a: dict, b: dict) -> bool:
    return condition_pairs(a).issubset(condition_pairs(b))


def merge_conditions(a: dict, b: dict) -> dict:
    merged: dict[str, object] = {}
    keys = set((a or {}).keys()) | set((b or {}).keys())
    for key in keys:
        av = (a or {}).get(key)
        bv = (b or {}).get(key)
        if av is None or bv is None:
            continue
        if isinstance(av, list) and isinstance(bv, list):
            inter = sorted(set(av) & set(bv))
            if inter:
                merged[key] = inter
        elif av == bv:
            merged[key] = av
    return canonicalize_conditions(merged)


def habit_is_self_write(habit: dict) -> bool:
    conditions = habit.get("conditions", {})
    prov_all = set(conditions.get("signalProvenanceAllIn", []))
    prov_any = set(conditions.get("signalProvenanceAnyOf", []))
    combined = prov_all | prov_any
    return "self-write" in combined and not ({"user-change", "real-desktop-change"} & combined)


def retention_score(habit: dict) -> float:
    stats = habit.get("stats", {})
    score = 0.0
    if habit.get("enabled", True):
        score += 3.0
    score += float(stats.get("confidence", DEFAULT_HABIT_CONFIDENCE)) * 2.0
    score += float(stats.get("success", 0)) * 0.15
    score -= float(stats.get("failure", 0)) * 0.2
    updated_minutes = minutes_since(stats.get("updatedAt") or stats.get("compiledAt"))
    if updated_minutes is not None:
        score -= min(updated_minutes / 1440.0, 2.0)
    if habit_is_self_write(habit):
        score -= 0.75
    if habit.get("source") == "auto-compiled-from-learning_update":
        score -= 0.15
    return round(score, 3)


def ensure_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def apply_decay(procedural_memory: dict) -> list[dict]:
    policy = procedural_memory.setdefault("policy", {})
    decay_after_hours = float(policy.get("decayAfterIdleHours", 24))
    decay_step = float(policy.get("decayStep", 0.08))
    disable_at = float(policy.get("disableAtConfidence", 0.55))
    changes: list[dict] = []

    for habit in procedural_memory.get("habits", []):
        if habit.get("source") != "auto-compiled-from-learning_update":
            continue
        stats = habit.setdefault("stats", {})
        updated = stats.get("updatedAt") or stats.get("compiledAt")
        idle_minutes = minutes_since(updated)
        if idle_minutes is None:
            continue
        idle_hours = idle_minutes / 60.0
        decay_bucket = int(idle_hours // max(decay_after_hours, 1.0))
        applied_bucket = int(stats.get("appliedDecayBucket", 0))
        if decay_bucket <= applied_bucket:
            continue
        steps = decay_bucket - applied_bucket
        old_conf = float(stats.get("confidence", DEFAULT_HABIT_CONFIDENCE))
        new_conf = round(clamp_unit(old_conf - steps * decay_step), 2)
        stats["confidence"] = new_conf
        stats["appliedDecayBucket"] = decay_bucket
        stats["decayedAt"] = now_iso()
        if new_conf <= disable_at:
            habit["enabled"] = False
        changes.append({
            "habitId": habit.get("id"),
            "oldConfidence": old_conf,
            "newConfidence": new_conf,
            "decayBucket": decay_bucket,
        })
    return changes


def prune_habits(procedural_memory: dict) -> list[str]:
    policy = procedural_memory.setdefault("policy", {})
    max_habits = int(policy.get("maxHabits", 12))
    prune_confidence = float(policy.get("pruneLowConfidenceAt", 0.75))
    pruned_ids: list[str] = []

    habits = procedural_memory.setdefault("habits", [])
    kept: list[dict] = []
    for habit in habits:
        stats = habit.get("stats", {})
        confidence = float(stats.get("confidence", DEFAULT_HABIT_CONFIDENCE))
        if (
            habit.get("enabled", True) is False
            and habit.get("source") == "auto-compiled-from-learning_update"
            and confidence <= prune_confidence
            and (habit_is_self_write(habit) or float(stats.get("failure", 0)) >= float(stats.get("success", 0)))
        ):
            pruned_ids.append(habit.get("id", "unknown"))
            continue
        kept.append(habit)

    if len(kept) > max_habits:
        ranked = sorted(kept, key=retention_score, reverse=True)
        removed = ranked[max_habits:]
        kept = ranked[:max_habits]
        pruned_ids.extend([habit.get("id", "unknown") for habit in removed])

    procedural_memory["habits"] = kept
    return pruned_ids


def find_matching_habit(procedural_memory: dict, event: str, action: str, conditions: dict) -> dict | None:
    for habit in procedural_memory.get("habits", []):
        if habit.get("triggerEvent") != event:
            continue
        if habit.get("preferredAction") != action:
            continue
        if same_conditions(habit.get("conditions", {}), conditions):
            return habit
    return None


def merge_candidate_score(habit: dict, conditions: dict) -> float:
    existing = habit.get("conditions", {})
    if same_conditions(existing, conditions):
        return 1.0
    overlap = len(condition_pairs(existing) & condition_pairs(conditions))
    union = len(condition_pairs(existing) | condition_pairs(conditions))
    if union == 0:
        return 0.0
    score = overlap / union
    if is_subset_conditions(existing, conditions) or is_subset_conditions(conditions, existing):
        score += 0.25
    return round(score, 3)


def find_merge_candidate(procedural_memory: dict, event: str, action: str, conditions: dict) -> dict | None:
    policy = procedural_memory.get("policy", {})
    if not policy.get("mergeBySubsetConditions", True):
        return None
    candidates: list[tuple[float, dict]] = []
    for habit in procedural_memory.get("habits", []):
        if habit.get("triggerEvent") != event:
            continue
        if habit.get("preferredAction") != action:
            continue
        score = merge_candidate_score(habit, conditions)
        if score >= 0.5:
            candidates.append((score, habit))
    if not candidates:
        return None
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def ensure_procedural_memory() -> dict:
    if PROCEDURAL_MEMORY.exists():
        data = load_json(PROCEDURAL_MEMORY)
        policy = data.setdefault("policy", {})
        policy.setdefault("compileAfterObservedSuccesses", 3)
        policy.setdefault("downgradeAfterFailures", 2)
        policy.setdefault("pruneLowConfidenceAt", 0.75)
        policy.setdefault("decayAfterIdleHours", 24)
        policy.setdefault("decayStep", 0.08)
        policy.setdefault("disableAtConfidence", 0.55)
        policy.setdefault("recencyFloorFactor", 0.65)
        policy.setdefault("mergeBySubsetConditions", True)
        policy.setdefault("maxHabits", 12)
        return data
    return {
        "purpose": "把重复成功的判断编译成低成本可复用习惯，在需要时先走程序化层，再决定是否升级为高成本推理。",
        "policy": {
            "preferExistingActions": True,
            "safeActionsOnlyByDefault": True,
            "compileAfterObservedSuccesses": 3,
            "downgradeAfterFailures": 2,
            "pruneLowConfidenceAt": 0.75,
            "decayAfterIdleHours": 24,
            "decayStep": 0.08,
            "disableAtConfidence": 0.55,
            "recencyFloorFactor": 0.65,
            "mergeBySubsetConditions": True,
            "maxHabits": 12,
        },
        "habits": [],
        "updatedAt": now_iso(),
    }


def update_procedural_memory(args: argparse.Namespace, state: dict) -> dict | None:
    if args.bucket != "action" or not args.event:
        return None

    procedural_memory = ensure_procedural_memory()
    policy = procedural_memory.setdefault("policy", {})
    threshold = int(policy.get("compileAfterObservedSuccesses", 3))
    downgrade_after_failures = int(policy.get("downgradeAfterFailures", 2))
    max_habits = int(policy.get("maxHabits", 12))

    decay_changes = apply_decay(procedural_memory)

    conditions = build_conditions(args)
    signature = make_signature(args.event, args.name, conditions)
    signature_key = make_signature_key(signature)

    observations = state.get("proceduralObservations")
    if not isinstance(observations, dict):
        legacy = ensure_list(observations)
        if legacy:
            recent = ensure_list(state.get("proceduralObservationLog"))
            recent.extend([item for item in legacy if isinstance(item, dict)])
            state["proceduralObservationLog"] = recent[-40:]
        observations = {}
        state["proceduralObservations"] = observations
    obs = observations.setdefault(
        signature_key,
        {
            "event": args.event,
            "action": args.name,
            "conditions": conditions,
            "successes": 0,
            "failures": 0,
            "compiled": False,
            "mergedInto": None,
            "firstSeenAt": now_iso(),
        },
    )
    if args.result == "success":
        obs["successes"] = int(obs.get("successes", 0)) + 1
    else:
        obs["failures"] = int(obs.get("failures", 0)) + 1
    obs["lastResult"] = args.result
    obs["lastSeenAt"] = now_iso()
    if args.note:
        obs["lastNote"] = args.note

    habit = find_matching_habit(procedural_memory, args.event, args.name, conditions)
    merged_into: str | None = None
    compiled = False

    if habit is None and args.result == "success" and int(obs.get("successes", 0)) >= threshold:
        merge_candidate = find_merge_candidate(procedural_memory, args.event, args.name, conditions)
        if merge_candidate is not None:
            habit = merge_candidate
            merged_into = habit.get("id")
            habit["conditions"] = merge_conditions(habit.get("conditions", {}), conditions) or canonicalize_conditions(habit.get("conditions", {}))
            merged_from = ensure_list(habit.get("compiledFrom"))
            if signature_key not in merged_from:
                merged_from.append(signature_key)
            habit["compiledFrom"] = merged_from
            obs["compiled"] = True
            obs["mergedInto"] = merged_into
        else:
            habit_id = f"auto-{slugify(args.event)}-{slugify(args.name)}-{len(procedural_memory.get('habits', [])) + 1}"
            habit = {
                "id": habit_id,
                "triggerEvent": args.event,
                "conditions": conditions,
                "preferredAction": args.name,
                "boost": DEFAULT_HABIT_BOOST,
                "source": "auto-compiled-from-learning_update",
                "compiledFrom": [signature_key],
                "enabled": True,
                "stats": {
                    "success": int(obs.get("successes", 0)),
                    "failure": int(obs.get("failures", 0)),
                    "confidence": DEFAULT_HABIT_CONFIDENCE,
                    "compiledAt": now_iso(),
                },
            }
            habits = procedural_memory.setdefault("habits", [])
            habits.append(habit)
            if len(habits) > max_habits:
                del habits[:-max_habits]
            obs["compiled"] = True
            compiled = True

    if habit is not None:
        stats = habit.setdefault("stats", {})
        stats.setdefault("success", 0)
        stats.setdefault("failure", 0)
        stats.setdefault("confidence", DEFAULT_HABIT_CONFIDENCE)
        if args.result == "success":
            stats["success"] = int(stats.get("success", 0)) + 1
            stats["confidence"] = round(clamp_unit(float(stats.get("confidence", DEFAULT_HABIT_CONFIDENCE)) + 0.08), 2)
            habit["boost"] = round(clamp(float(habit.get("boost", DEFAULT_HABIT_BOOST)) + 0.03, 0.1, 1.5), 2)
            habit["enabled"] = True
        else:
            stats["failure"] = int(stats.get("failure", 0)) + 1
            stats["confidence"] = round(clamp_unit(float(stats.get("confidence", DEFAULT_HABIT_CONFIDENCE)) - 0.12), 2)
            habit["boost"] = round(clamp(float(habit.get("boost", DEFAULT_HABIT_BOOST)) - 0.05, 0.1, 1.5), 2)
            if int(stats.get("failure", 0)) >= downgrade_after_failures and int(stats.get("failure", 0)) >= int(stats.get("success", 0)):
                habit["enabled"] = False
        if args.note:
            stats["lastNote"] = args.note
        stats["updatedAt"] = now_iso()
        obs["compiled"] = True
        if merged_into:
            obs["mergedInto"] = merged_into

    pruned_ids = prune_habits(procedural_memory)
    procedural_memory["updatedAt"] = now_iso()
    save_json(PROCEDURAL_MEMORY, procedural_memory)

    return {
        "signatureKey": signature_key,
        "observedSuccesses": obs.get("successes", 0),
        "observedFailures": obs.get("failures", 0),
        "compiled": compiled,
        "mergedInto": merged_into,
        "habitId": habit.get("id") if habit else None,
        "habitEnabled": habit.get("enabled") if habit else None,
        "habitBoost": habit.get("boost") if habit else None,
        "habitConfidence": habit.get("stats", {}).get("confidence") if habit else None,
        "decayChanges": decay_changes,
        "prunedHabitIds": pruned_ids,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bucket", choices=["event", "action", "skill"], required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--result", choices=["success", "failure"], required=True)
    parser.add_argument("--amount", type=float, default=DEFAULT_STEP)
    parser.add_argument("--note")
    parser.add_argument("--event")
    parser.add_argument("--requires-current-focus", action="store_true")
    parser.add_argument("--requires-no-signals", action="store_true")
    parser.add_argument("--signal-types-all-in")
    parser.add_argument("--signal-types-any-of")
    parser.add_argument("--signal-types-none-of")
    parser.add_argument("--signal-provenance-all-in")
    parser.add_argument("--signal-provenance-any-of")
    parser.add_argument("--signal-provenance-none-of")
    args = parser.parse_args()

    state = load_json(LEARNING_STATE)
    weights = state.setdefault("weights", {})
    bucket_map = {
        "event": "eventPriority",
        "action": "actionPriority",
        "skill": "skillPriority",
    }
    bucket_name = bucket_map[args.bucket]
    bucket = weights.setdefault(bucket_name, {})
    current = float(bucket.get(args.name, 1.0))

    delta = args.amount if args.result == "success" else -args.amount
    updated = clamp(current + delta)
    bucket[args.name] = round(updated, 3)

    history = state.setdefault("weightUpdates", [])
    history.append(
        {
            "timestamp": now_iso(),
            "bucket": args.bucket,
            "name": args.name,
            "result": args.result,
            "old": round(current, 3),
            "new": round(updated, 3),
            "note": args.note,
            "event": args.event,
        }
    )
    if len(history) > 100:
        del history[:-100]

    procedural_result = update_procedural_memory(args, state)

    state["updatedAt"] = now_iso()
    save_json(LEARNING_STATE, state)

    print(json.dumps({
        "ok": True,
        "bucket": args.bucket,
        "name": args.name,
        "old": round(current, 3),
        "new": round(updated, 3),
        "procedural": procedural_result,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
