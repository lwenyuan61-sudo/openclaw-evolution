from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
AUTO = ROOT / "autonomy"
ACTION_STATE_PATH = CORE / "action-state.json"
PERCEPTION_PATH = CORE / "perception-state.json"
SELF_STATE_PATH = CORE / "self-state.json"
CONTINUITY_PATH = AUTO / "continuity-state.json"
RESIDENT_CONFIG_PATH = CORE / "resident-config.json"
CAPABILITY_PATH = CORE / "capability-registry.json"
TASK_STATE_PATH = STATE / "resident_task_state.json"
HELP_FOLLOW_TASK_ID = "follow-help-evidence-connector"
HELP_FOLLOW_COOLDOWN_MINUTES = 30.0
DEFAULT_ALLOWED_ACTIONS = [
    "continue-focus",
    "inspect-local-signal",
    "run-consistency-check",
    "refresh-device-state",
    "refresh-screen-state",
    "silent-wait",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_iso(value: str | None):
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except Exception:
        return None


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def read_text_preview(path: Path, *, max_lines: int = 8, max_chars: int = 800) -> tuple[bool, str | None, int | None]:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return False, None, None
    lines = text.splitlines()
    preview = "\n".join(lines[:max_lines]).strip()
    if len(preview) > max_chars:
        preview = preview[:max_chars] + "…"
    return True, (preview or None), len(lines)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def stable_json_hash(payload: dict) -> str:
    body = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()[:16]


def help_evidence_fingerprint(help_packet: dict, useful_actions: list[dict]) -> str:
    recommendation = help_packet.get("recommendation", {}) if isinstance(help_packet.get("recommendation"), dict) else {}
    verification = help_packet.get("verification", {}) if isinstance(help_packet.get("verification"), dict) else {}
    stable_actions = [
        {"id": item.get("id"), "kind": item.get("kind"), "safe": item.get("safe"), "source": item.get("source")}
        for item in useful_actions
    ]
    return stable_json_hash({
        "actions": stable_actions,
        "recommendationMode": recommendation.get("mode"),
        "shouldSurfaceToLee": bool(recommendation.get("shouldSurfaceToLee")),
        "verificationStatus": verification.get("status"),
    })


def adaptive_cooldown_minutes(base_minutes: float, repeat_count: int, success_count: int, failure_count: int, *, status: str) -> float:
    base = max(float(base_minutes), 0.5)
    repeats = max(int(repeat_count or 0), 0)
    successes = max(int(success_count or 0), 0)
    failures = max(int(failure_count or 0), 0)
    if status == "ok":
        # Same-evidence repeats are the clearest sign that the cerebellum should
        # back off.  Long success streaks with no failures also increase cooldown
        # slightly because the action is stable and does not need constant proof.
        multiplier = 1.0 + min(repeats, 8) * 0.5
        if successes >= 3 and failures == 0:
            multiplier += min((successes - 2) * 0.15, 1.5)
        return round(min(base * multiplier, 240.0), 2)
    # Failures should retry sooner than successful repeats, but not thrash.
    return round(min(max(5.0, base * 0.5) * (1.0 + min(failures, 5) * 0.25), 60.0), 2)


def update_task_state(task_id: str, fingerprint: str | None, status: str, *, artifact_path: str | None = None, note: str | None = None) -> dict:
    task_state = load_optional_json(TASK_STATE_PATH)
    now = now_iso()
    tasks = task_state.setdefault("tasks", {})
    task = tasks.setdefault(task_id, {"id": task_id, "createdAt": now, "successCount": 0, "failureCount": 0, "repeatCount": 0, "outcomes": []})
    same_fingerprint = bool(fingerprint and task.get("lastEvidenceFingerprint") == fingerprint)
    if same_fingerprint:
        task["repeatCount"] = int(task.get("repeatCount", 0) or 0) + 1
    else:
        task["repeatCount"] = 0
    task["status"] = "completed" if status == "ok" else "attention-needed"
    task["phase"] = "cooldown" if status == "ok" else "review"
    task["lastEvidenceFingerprint"] = fingerprint
    task["lastCompletedAt"] = now
    task["lastArtifactPath"] = artifact_path
    task["lastNote"] = note
    if status == "ok":
        task["successCount"] = int(task.get("successCount", 0) or 0) + 1
        task["cooldownMinutes"] = adaptive_cooldown_minutes(HELP_FOLLOW_COOLDOWN_MINUTES, int(task.get("repeatCount", 0) or 0), int(task.get("successCount", 0) or 0), int(task.get("failureCount", 0) or 0), status="ok")
        task["cooldownUntil"] = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=float(task["cooldownMinutes"]))).isoformat(timespec="seconds")
    else:
        task["failureCount"] = int(task.get("failureCount", 0) or 0) + 1
        task["cooldownMinutes"] = adaptive_cooldown_minutes(5.0, int(task.get("repeatCount", 0) or 0), int(task.get("successCount", 0) or 0), int(task.get("failureCount", 0) or 0), status="warning")
        task["cooldownUntil"] = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=float(task["cooldownMinutes"]))).isoformat(timespec="seconds")
    task.setdefault("outcomes", []).append({"timestamp": now, "status": status, "fingerprint": fingerprint, "artifactPath": artifact_path, "note": note})
    task["outcomes"] = trim_list(task["outcomes"], 20)
    task_state["updatedAt"] = now
    task_state["policy"] = {
        "purpose": "resident task-state/cooldown/outcome memory for low-level cerebellum actions",
        "sameEvidenceRepeatsShouldCooldown": True,
        "adaptiveCooldown": True,
        "visibleContact": False,
    }
    save_json(TASK_STATE_PATH, task_state)
    return task


GENERIC_ACTION_LIFECYCLE = {
    "continue-focus": {"phase": "maintain", "cooldownMinutes": 2.0, "cooldownAfterRepeats": 4},
    "silent-wait": {"phase": "cooldown", "cooldownMinutes": 2.0, "cooldownAfterRepeats": 6},
    "inspect-local-signal": {"phase": "verify", "cooldownMinutes": 5.0, "cooldownAfterRepeats": 2},
    "run-consistency-check": {"phase": "verify", "cooldownMinutes": 10.0, "cooldownAfterRepeats": 1},
    "refresh-device-state": {"phase": "observe", "cooldownMinutes": 20.0, "cooldownAfterRepeats": 1},
    "refresh-screen-state": {"phase": "observe", "cooldownMinutes": 5.0, "cooldownAfterRepeats": 1},
}


def generic_action_fingerprint(action: str, ctx: dict, result: dict) -> str:
    review = result.get("review", {}) if isinstance(result.get("review"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else ctx.get("primarySignal")
    payload = {
        "action": action,
        "eventSignalTypes": ctx.get("signalTypes", []),
        "eventSignalProvenances": ctx.get("signalProvenances", []),
        "primaryType": primary.get("type") if isinstance(primary, dict) else None,
        "primaryProvenance": primary.get("provenance") if isinstance(primary, dict) else None,
        "resultStatus": result.get("status"),
        "resultMode": result.get("mode"),
    }
    return stable_json_hash(payload)


def record_generic_action_lifecycle(action: str, ctx: dict, result: dict) -> dict | None:
    if action == HELP_FOLLOW_TASK_ID or action not in GENERIC_ACTION_LIFECYCLE:
        return None
    spec = GENERIC_ACTION_LIFECYCLE[action]
    task_state = load_optional_json(TASK_STATE_PATH)
    now = now_iso()
    tasks = task_state.setdefault("tasks", {})
    task = tasks.setdefault(action, {"id": action, "createdAt": now, "successCount": 0, "failureCount": 0, "repeatCount": 0, "outcomes": []})
    fingerprint = generic_action_fingerprint(action, ctx, result)
    same_fingerprint = bool(task.get("lastEvidenceFingerprint") == fingerprint)
    if same_fingerprint:
        task["repeatCount"] = int(task.get("repeatCount", 0) or 0) + 1
    else:
        task["repeatCount"] = 0
    ok = result.get("status") == "ok"
    task["status"] = "completed" if ok else "attention-needed"
    task["phase"] = spec.get("phase", "verify") if ok else "review"
    task["lastEvidenceFingerprint"] = fingerprint
    task["lastCompletedAt"] = now
    task["lastNote"] = f"resident-generic-lifecycle-{action}"
    if ok:
        task["successCount"] = int(task.get("successCount", 0) or 0) + 1
    else:
        task["failureCount"] = int(task.get("failureCount", 0) or 0) + 1
    cooldown_after = int(spec.get("cooldownAfterRepeats", 1) or 1)
    should_cooldown = ok and (cooldown_after <= 1 or int(task.get("repeatCount", 0) or 0) >= cooldown_after)
    task["cooldownAfterRepeats"] = cooldown_after
    task["cooldownMinutes"] = float(spec.get("cooldownMinutes", 5.0))
    if should_cooldown:
        task["phase"] = "cooldown"
        task["cooldownMinutes"] = adaptive_cooldown_minutes(float(spec.get("cooldownMinutes", 5.0)), int(task.get("repeatCount", 0) or 0), int(task.get("successCount", 0) or 0), int(task.get("failureCount", 0) or 0), status="ok")
        task["cooldownUntil"] = (datetime.now(timezone.utc).astimezone() + timedelta(minutes=float(task["cooldownMinutes"]))).isoformat(timespec="seconds")
    else:
        task["cooldownUntil"] = task.get("cooldownUntil") if task.get("phase") == "cooldown" else None
    outcome = {
        "timestamp": now,
        "status": result.get("status"),
        "phase": task.get("phase"),
        "fingerprint": fingerprint,
        "repeatCount": task.get("repeatCount", 0),
        "cooldownUntil": task.get("cooldownUntil"),
    }
    task.setdefault("outcomes", []).append(outcome)
    task["outcomes"] = trim_list(task["outcomes"], 20)
    task_state["updatedAt"] = now
    task_state["policy"] = {
        "purpose": "resident task-state/cooldown/outcome memory for low-level cerebellum actions",
        "sameEvidenceRepeatsShouldCooldown": True,
        "adaptiveCooldown": True,
        "visibleContact": False,
        "genericLifecycleEnabled": True,
    }
    save_json(TASK_STATE_PATH, task_state)
    return {
        "taskId": action,
        "phase": task.get("phase"),
        "status": task.get("status"),
        "repeatCount": task.get("repeatCount", 0),
        "cooldownUntil": task.get("cooldownUntil"),
        "fingerprint": fingerprint,
    }


def load_capability_registry() -> dict:
    return load_optional_json(CAPABILITY_PATH)


def ability_map(capability_registry: dict) -> dict[str, dict]:
    abilities = list(capability_registry.get("abilities", []) or [])
    return {
        item.get("id"): item
        for item in abilities
        if isinstance(item, dict) and item.get("id")
    }


def action_capability_meta(action: str, capability_registry: dict) -> dict:
    resident_actions = capability_registry.get("residentActions", {}) if isinstance(capability_registry.get("residentActions"), dict) else {}
    meta = resident_actions.get(action, {}) if isinstance(resident_actions.get(action), dict) else {}
    abilities = ability_map(capability_registry)
    capability_id = meta.get("capabilityId")
    capability = abilities.get(capability_id, {}) if capability_id else {}
    return {
        "capabilityId": capability_id,
        "capabilityDomain": capability.get("domain"),
        "preferredSkill": meta.get("preferredSkill"),
        "safeReadOnly": bool(meta.get("safeReadOnly", action in DEFAULT_ALLOWED_ACTIONS)),
        "requiresAbilities": list(meta.get("requiresAbilities", []) or []),
    }


def attach_capability_metadata(payload: dict, action: str, capability_registry: dict) -> dict:
    meta = action_capability_meta(action, capability_registry)
    payload["capabilityId"] = meta.get("capabilityId")
    payload["capabilityDomain"] = meta.get("capabilityDomain")
    payload["preferredSkill"] = meta.get("preferredSkill")
    return payload


def trim_list(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def run_python(script: Path, *args: str) -> tuple[int, str, str]:
    creationflags = 0
    if sys.platform.startswith("win"):
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=creationflags,
    )
    return proc.returncode, proc.stdout.strip(), proc.stderr.strip()


def parse_json_output(text: str) -> dict | None:
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        return None


def latest_signals(perception: dict) -> list[dict]:
    signals = perception.get("lastProbeSignals")
    if signals is None:
        signals = perception.get("recentSignals", [])[-5:]
    return list(signals or [])


def latest_suppressed_signals(perception: dict) -> list[dict]:
    signals = perception.get("lastSuppressedSignals")
    if signals is None:
        signals = perception.get("recentSuppressedSignals", [])[-5:]
    return list(signals or [])


def unique_strings(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def sanitize_json_value(value):
    if isinstance(value, str):
        return ''.join(ch for ch in value if ch == '\n' or ch == '\t' or ord(ch) >= 32)
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_json_value(item) for key, item in value.items()}
    return value


def signal_context() -> dict:
    perception = load_optional_json(PERCEPTION_PATH)
    self_state = load_optional_json(SELF_STATE_PATH)
    continuity = load_optional_json(CONTINUITY_PATH)
    emitted = latest_signals(perception)
    suppressed = latest_suppressed_signals(perception)
    primary = emitted[0] if emitted else None
    return {
        "perception": perception,
        "selfState": self_state,
        "continuity": continuity,
        "focus": self_state.get("currentFocus"),
        "hasFocus": bool(self_state.get("currentFocus")),
        "emittedSignals": emitted,
        "suppressedSignals": suppressed,
        "primarySignal": primary,
        "signalTypes": unique_strings([sig.get("type") for sig in emitted]),
        "signalProvenances": unique_strings([sig.get("provenance") for sig in emitted]),
    }


def semantic_writeback_payload(action: str, result: dict) -> dict | None:
    review = result.get("review") if isinstance(result.get("review"), dict) else {}
    verification = result.get("verification") if isinstance(result.get("verification"), dict) else {}
    verification_parsed = verification.get("parsed", {}) if isinstance(verification.get("parsed"), dict) else {}
    primary = review.get("primarySignal") if isinstance(review.get("primarySignal"), dict) else {}

    if action in {"continue-focus", "silent-wait"} and review:
        # Low-power resident actions used to leave no durable semantic trace, so
        # repeated maintain/continue-focus pulses looked like an evidence gap to
        # later opportunity gates.  Treat the maintenance decision itself as a
        # small S1 semantic writeback: it is not a new opportunity, but it is
        # evidence that the latest signal was deliberately kept inside the cheap
        # loop.
        if primary:
            signal_type = primary.get("type", "local-signal")
            provenance = primary.get("provenance", "unknown-provenance")
            last_action = (
                f"resident kept a {provenance} {signal_type} in S1 after semantic triage instead of escalating it as a Lee-facing opportunity"
            )
        else:
            last_action = "resident recorded a quiet S1 maintenance decision as semantic evidence instead of leaving another raw continue-focus tick"
        return {
            "lastAction": last_action,
            "stopPoint": "continue-focus / silent-wait 现在会写回一条轻量语义证据，避免低价值维护循环被误判成缺少 semantic writeback。",
            "nextStep": "继续观察 reachOutGate / opportunity 是否因维护态语义证据而减少 missing-semantic-writeback；若仍空转，再推进 owner-chat ingestion auto-hook。",
        }

    if action == "inspect-local-signal" and verification.get("status") == "ok" and primary:
        signal_type = primary.get("type", "local-signal")
        provenance = primary.get("provenance", "unknown-provenance")
        if signal_type == "workspace-changed":
            path = primary.get("path") or verification_parsed.get("path") or "workspace artifact"
            return {
                "lastAction": (
                    f"resident verified a {provenance} workspace artifact change at {path} using mtime/content-hash identity evidence and preserved it for opportunity triage"
                ),
                "stopPoint": "非屏幕 artifact 信号现在不再只按 workspace-changed 泛类处理，而会携带 path、oldContentHash、newContentHash 等身份证据进入语义机会判断。",
                "nextStep": "下一步观察 artifact 身份证据是否能稳定降低误合并/误唤醒；若有效，把同样结构扩到 device/audio 等非屏幕信号。",
            }
        return {
            "lastAction": (
                f"resident successfully verified a {provenance} {signal_type} through a read-only reality check and now preserves it as semantic opportunity evidence instead of letting it stay only as a raw action result"
            ),
            "stopPoint": "现在 inspect-local-signal 的已验证结果不再只是动作日志，它会继续喂给语义判断层，帮助系统区分『候选机会』和『值得本人格接手』；下一处缺口是把这套判断扩到更多非屏幕信号",
            "nextStep": "下一步优先观察这种『先验证，再做语义解释，再决定是否上浮』的方式是否稳定降低误唤醒；如果有效，再把同样结构扩到更多能力域。",
        }

    if action == "follow-help-evidence-connector" and verification.get("status") == "ok":
        selected = verification_parsed.get("selectedUsefulAction") if isinstance(verification_parsed.get("selectedUsefulAction"), dict) else {}
        useful_id = selected.get("id") or "prepared-help-evidence"
        return {
            "lastAction": (
                f"resident verified prepared Lee-service help evidence as the local connector {useful_id} and wrote the result back as durable S1 semantic evidence without surfacing to Lee"
            ),
            "stopPoint": "follow-help-evidence-connector 的已验证本地结果现在会写回 semantic evidence，避免 reachOutGate 把已完成的安静准备误判成 missing-semantic-writeback。",
            "nextStep": "下一步观察 reachOutGate.mustRequirements 是否在已验证 help-evidence 路径中减少 missing-semantic-writeback；若仍存在，再把同样写回扩展到更多 resident-safe 本地动作。",
        }

    return None


def apply_semantic_writeback(action: str, result: dict) -> dict:
    payload = semantic_writeback_payload(action, result)
    if not payload:
        return {"applied": False, "reason": "no-semantic-writeback-for-result"}

    self_state = load_optional_json(SELF_STATE_PATH)
    continuity = load_optional_json(CONTINUITY_PATH)
    if not self_state or not continuity:
        return {"applied": False, "reason": "missing-self-or-continuity-state"}

    changed = False
    for key in ("lastAction", "stopPoint", "nextStep"):
        if self_state.get(key) != payload[key]:
            self_state[key] = payload[key]
            changed = True

    if not changed:
        return {"applied": True, "reason": "semantic-state-already-current", "lastAction": self_state.get("lastAction")}

    timestamp = now_iso()
    self_state["lastMeaningfulProgressAt"] = timestamp
    self_state["updatedAt"] = timestamp

    continuity["currentFocus"] = self_state.get("currentFocus")
    continuity["lastAction"] = self_state.get("lastAction")
    continuity["currentStopPoint"] = self_state.get("stopPoint")
    continuity["nextLikelyStep"] = self_state.get("nextStep")
    continuity["updatedAt"] = timestamp

    save_json(SELF_STATE_PATH, self_state)
    save_json(CONTINUITY_PATH, continuity)

    return {
        "applied": True,
        "timestamp": timestamp,
        "lastAction": self_state.get("lastAction"),
        "stopPoint": self_state.get("stopPoint"),
        "nextStep": self_state.get("nextStep"),
    }


def summarize_signal_review(action: str, score: float | None, ctx: dict) -> dict:
    primary = ctx.get("primarySignal")
    emitted = ctx.get("emittedSignals", [])
    suppressed = ctx.get("suppressedSignals", [])
    return {
        "timestamp": now_iso(),
        "selectedAction": action,
        "score": score,
        "focus": ctx.get("focus"),
        "nextLikelyStep": None,
        "primarySignal": primary,
        "emittedSignalCount": len(emitted),
        "suppressedSignalCount": len(suppressed),
        "emittedSignals": emitted,
        "suppressedSignals": suppressed,
        "summary": (
            "resident reviewed the latest local signal and kept it inside the internal loop"
            if primary
            else "resident reviewed the quiet state and found no emitted local signal"
        ),
    }


def json_result(note: str, payload: dict, *, ok: bool = True) -> dict:
    parsed = {
        **payload,
        "status": "ok" if ok else payload.get("status", "warning"),
        "safeReadOnly": True,
        "note": note,
    }
    return {
        "status": "ok" if ok else "warning",
        "returncode": 0 if ok else 1,
        "stdout": json.dumps(parsed, ensure_ascii=False, indent=2),
        "stderr": "",
        "parsed": parsed,
        "note": note,
    }


def verify_workspace_signal(ctx: dict) -> dict:
    note = "resident-inspect-local-signal-workspace-read"
    primary = ctx.get("primarySignal") if isinstance(ctx.get("primarySignal"), dict) else {}
    rel_path = primary.get("path")
    if not rel_path:
        return json_result(note, {"reason": "missing-workspace-path"}, ok=False)

    target = ROOT / Path(rel_path)
    exists = target.exists()
    signal_mtime = primary.get("latestMtime")
    observed_mtime = None
    mtime_matches_signal = False
    observed_hash = None
    content_hash_matches_signal = False
    text_preview_available = False
    text_preview = None
    line_count = None
    artifact_kind = None
    if exists:
        observed_mtime = datetime.fromtimestamp(target.stat().st_mtime, tz=timezone.utc).astimezone().isoformat(timespec="seconds")
        signal_dt = parse_iso(signal_mtime)
        observed_dt = parse_iso(observed_mtime)
        if signal_dt and observed_dt:
            mtime_matches_signal = abs((observed_dt - signal_dt).total_seconds()) <= 2.0
        observed_hash = file_sha256(target)
        signaled_hash = primary.get("newContentHash")
        content_hash_matches_signal = bool(signaled_hash and observed_hash == signaled_hash)
        text_preview_available, text_preview, line_count = read_text_preview(target)
        if target.suffix.lower() == ".md":
            artifact_kind = "markdown-note"
        elif target.suffix.lower() == ".json":
            artifact_kind = "json-artifact"
        elif target.suffix.lower() == ".py":
            artifact_kind = "python-source"
        elif text_preview_available:
            artifact_kind = "text-artifact"
        else:
            artifact_kind = "binary-artifact"

    payload = {
        "path": rel_path,
        "exists": exists,
        "isFile": target.is_file() if exists else False,
        "signalLatestMtime": signal_mtime,
        "observedLatestMtime": observed_mtime,
        "mtimeMatchesSignal": mtime_matches_signal,
        "observedContentHash": observed_hash,
        "contentHashMatchesSignal": content_hash_matches_signal,
        "artifactKind": artifact_kind,
        "artifactDiffAvailable": bool(primary.get("artifactDiffAvailable")),
        "contentPreviewAvailable": text_preview_available,
        "contentPreview": text_preview,
        "lineCount": line_count,
        "provenance": primary.get("provenance"),
        "signalType": primary.get("type"),
    }
    hash_ok = primary.get("newContentHash") is None or content_hash_matches_signal
    return json_result(note, payload, ok=bool(exists and (signal_mtime is None or mtime_matches_signal) and hash_ok))


def verify_device_snapshot_signal(ctx: dict) -> dict:
    note = "resident-inspect-local-signal-device-read"
    primary = ctx.get("primarySignal") if isinstance(ctx.get("primarySignal"), dict) else {}
    snapshot_path = STATE / "device_state_snapshot.json"
    if not snapshot_path.exists():
        return json_result(note, {"reason": "missing-device-snapshot"}, ok=False)

    snapshot = load_optional_json(snapshot_path)
    snapshot_summary = snapshot.get("summary") if isinstance(snapshot, dict) else None
    primary_summary = primary.get("summary") if isinstance(primary.get("summary"), dict) else None
    summary_matches = bool(snapshot_summary == primary_summary) if primary_summary is not None else False
    captured_matches = snapshot.get("capturedAt") == primary.get("capturedAt")
    payload = {
        "snapshotPath": str(snapshot_path),
        "snapshotPresent": True,
        "summaryMatchesSignal": summary_matches,
        "capturedAtMatchesSignal": captured_matches,
        "snapshotCapturedAt": snapshot.get("capturedAt"),
        "signalCapturedAt": primary.get("capturedAt"),
        "signalType": primary.get("type"),
    }
    return json_result(note, payload, ok=bool(summary_matches or captured_matches))


def run_reality_inspection(action: str, ctx: dict) -> dict:
    primary = ctx.get("primarySignal") if isinstance(ctx.get("primarySignal"), dict) else {}
    signal_type = primary.get("type")

    if signal_type == "workspace-changed":
        result = verify_workspace_signal(ctx)
    elif signal_type == "device-snapshot-present":
        result = verify_device_snapshot_signal(ctx)
    else:
        note = f"resident-{action}-reality-read"
        rc, stdout, stderr = run_python(CORE / "scripts" / "reality_action.py", "--intent", "inspect-cursor", "--execute", "--note", note)
        parsed = parse_json_output(stdout)
        result = {
            "status": "ok" if rc == 0 else "warning",
            "returncode": rc,
            "stdout": stdout,
            "stderr": stderr,
            "parsed": parsed,
            "note": note,
        }
        if parsed and parsed.get("status") in {"ok", "dry-run"}:
            result["status"] = "ok"

    result["primarySignal"] = primary or None
    return result


def run_help_evidence_followthrough(ctx: dict) -> dict:
    note = "resident-help-evidence-followthrough"
    rc_help, out_help, err_help = run_python(CORE / "scripts" / "lee_service_evidence_builder.py")
    rc_sem, out_sem, err_sem = run_python(CORE / "scripts" / "semantic_signal_layer.py", "--dry-run")
    rc_upgrade, out_upgrade, err_upgrade = run_python(CORE / "scripts" / "autonomy_upgrade_tick.py", "--dry-run")
    rc_consistency, out_consistency, err_consistency = run_python(CORE / "scripts" / "consistency_check.py", "--write", str(STATE / "consistency_report.json"))

    help_packet = load_optional_json(STATE / "lee_service_help_evidence.json")
    useful_actions = [item for item in list(help_packet.get("usefulActions", []) or []) if isinstance(item, dict)]
    local_help = [item for item in useful_actions if str(item.get("kind")) in {"continue-focus", "internal-connector"}]
    specific = next((item for item in local_help if item.get("id") == "refine-help-evidence-specific-resident-safe-connector"), None)
    # Keep the execution-side fingerprint aligned with action_ranker.py.  The
    # previous full-packet fingerprint included main-persona report actions, so
    # the ranker and task-state kept disagreeing and the resident repeated this
    # connector instead of honoring cooldown.
    fingerprint = help_evidence_fingerprint(help_packet, local_help)
    semantic = parse_json_output(out_sem) or {}
    upgrade = parse_json_output(out_upgrade) or {}
    consistency = parse_json_output(out_consistency) or {}
    ok = bool(
        rc_help == 0
        and rc_sem == 0
        and rc_upgrade == 0
        and rc_consistency == 0
        and specific
        and consistency.get("status") == "ok"
    )
    artifact = {
        "timestamp": now_iso(),
        "status": "ok" if ok else "warning",
        "note": note,
        "selectedUsefulAction": specific,
        "usefulActionIds": [item.get("id") for item in useful_actions],
        "evidenceFingerprint": fingerprint,
        "checks": {
            "leeServiceEvidenceBuilder": {"rc": rc_help, "stderr": err_help[-500:]},
            "semanticSignalLayerDryRun": {"rc": rc_sem, "candidateRequestIds": [item.get("id") for item in ((semantic.get("semanticSignalLayer") or {}).get("candidateRequests") or []) if isinstance(item, dict)], "stderr": err_sem[-500:]},
            "autonomyUpgradeTickDryRun": {"rc": rc_upgrade, "selected": (upgrade.get("selected") or {}).get("id") if isinstance(upgrade.get("selected"), dict) else None, "stderr": err_upgrade[-500:]},
            "consistencyCheck": {"rc": rc_consistency, "status": consistency.get("status"), "errors": consistency.get("errors"), "warnings": consistency.get("warnings"), "stderr": err_consistency[-500:]},
        },
        "policy": {
            "externalWrite": False,
            "visibleContact": False,
            "safeLocalFollowthrough": True,
        },
    }
    artifact_path = STATE / "help_evidence_followthrough.json"
    save_json(artifact_path, artifact)
    task_record = update_task_state(HELP_FOLLOW_TASK_ID, fingerprint, "ok" if ok else "warning", artifact_path=str(artifact_path), note=note)
    artifact["taskState"] = {
        "status": task_record.get("status"),
        "phase": task_record.get("phase"),
        "cooldownUntil": task_record.get("cooldownUntil"),
        "repeatCount": task_record.get("repeatCount"),
        "successCount": task_record.get("successCount"),
    }
    save_json(artifact_path, artifact)
    return {
        "status": "ok" if ok else "warning",
        "mode": "internal-review+local-verification",
        "stdout": json.dumps({"artifact": str(STATE / "help_evidence_followthrough.json"), "selectedUsefulActionId": specific.get("id") if specific else None, "ok": ok}, ensure_ascii=False),
        "stderr": "" if ok else "one or more followthrough checks were weak",
        "review": {
            **summarize_signal_review("follow-help-evidence-connector", None, ctx),
            "summary": "resident followed through prepared Lee-service help evidence into a verified local connector artifact",
            "helpEvidenceFollowthrough": artifact,
        },
        "verification": {"status": "ok" if ok else "warning", "parsed": artifact},
    }


def execute_action(action: str, score: float | None, resident_config: dict, ctx: dict, capability_registry: dict) -> dict:
    last_decision_path = ROOT / resident_config.get("lastDecisionPath", "state/resident_last_decision.json")

    if action == "continue-focus":
        review = summarize_signal_review(action, score, ctx)
        review["summary"] = "resident reaffirmed current focus without escalating"
        review = attach_capability_metadata(review, action, capability_registry)
        save_json(last_decision_path, review)
        return attach_capability_metadata({"status": "ok", "mode": "internal", "stdout": review["summary"], "stderr": "", "review": review}, action, capability_registry)

    if action == "silent-wait":
        review = summarize_signal_review(action, score, ctx)
        review["summary"] = "resident stayed quiet because emitted value was low"
        review = attach_capability_metadata(review, action, capability_registry)
        save_json(last_decision_path, review)
        return attach_capability_metadata({"status": "ok", "mode": "internal", "stdout": review["summary"], "stderr": "", "review": review}, action, capability_registry)

    if action == "inspect-local-signal":
        review = summarize_signal_review(action, score, ctx)
        verification = run_reality_inspection(action, ctx)
        review["verification"] = verification
        if verification.get("parsed", {}).get("stdout"):
            review["cursorPosition"] = verification["parsed"].get("stdout")
        if verification.get("status") == "ok":
            review["summary"] = "resident reviewed the latest local signal and completed a read-only reality check"
        else:
            review["summary"] = "resident reviewed the latest local signal but the follow-up reality check was weak"
        review = attach_capability_metadata(review, action, capability_registry)
        review_path = ROOT / resident_config.get("signalReviewPath", "state/resident_signal_review.json")
        save_json(review_path, review)
        save_json(last_decision_path, review)
        return attach_capability_metadata({
            "status": "ok" if verification.get("status") == "ok" else "warning",
            "mode": "internal-review+reality-read",
            "stdout": json.dumps(
                {
                    "reviewPath": str(review_path),
                    "primarySignal": review.get("primarySignal"),
                    "verification": verification.get("parsed") or verification,
                },
                ensure_ascii=False,
            ),
            "stderr": verification.get("stderr", ""),
            "review": review,
            "verification": verification,
        }, action, capability_registry)

    if action == "follow-help-evidence-connector":
        result = run_help_evidence_followthrough(ctx)
        return attach_capability_metadata(result, action, capability_registry)

    if action == "run-consistency-check":
        returncode, stdout, stderr = run_python(CORE / "scripts" / "consistency_check.py", "--write", str(STATE / "consistency_report.json"))
        return attach_capability_metadata({"status": "ok" if returncode == 0 else "warning", "mode": "python", "returncode": returncode, "stdout": stdout, "stderr": stderr}, action, capability_registry)

    if action == "refresh-device-state":
        returncode, stdout, stderr = run_python(ROOT / "skills" / "device-state" / "scripts" / "device_state.py", "--write-json", str(ROOT / resident_config.get("deviceSnapshotPath", "state/device_state_snapshot.json")))
        return attach_capability_metadata({"status": "ok" if returncode == 0 else "warning", "mode": "python", "returncode": returncode, "stdout": stdout, "stderr": stderr}, action, capability_registry)

    if action == "refresh-screen-state":
        returncode, stdout, stderr = run_python(
            ROOT / "skills" / "screen-state" / "scripts" / "screen_state.py",
            "--write-json", str(ROOT / resident_config.get("screenSnapshotJsonPath", "state/screen_state.json")),
            "--save-image", str(ROOT / resident_config.get("screenSnapshotImagePath", "state/screen_state.png")),
        )
        return attach_capability_metadata({"status": "ok" if returncode == 0 else "warning", "mode": "python", "returncode": returncode, "stdout": stdout, "stderr": stderr}, action, capability_registry)

    return attach_capability_metadata({"status": "skipped", "mode": "unsupported", "stdout": "", "stderr": f"unsupported action: {action}"}, action, capability_registry)


def learning_args_for_context(action: str, event: str, ctx: dict, result_status: str) -> list[str]:
    args = [
        "--bucket", "action",
        "--name", action,
        "--result", "success" if result_status == "ok" else "failure",
        "--amount", "0.01",
        "--event", event,
        "--note", f"resident-{action}-{result_status}",
    ]
    if ctx.get("hasFocus"):
        args.append("--requires-current-focus")
    if not ctx.get("emittedSignals"):
        args.append("--requires-no-signals")
    signal_types = ctx.get("signalTypes", [])
    if signal_types:
        args.extend(["--signal-types-any-of", ",".join(signal_types)])
    signal_provenances = ctx.get("signalProvenances", [])
    if signal_provenances:
        args.extend(["--signal-provenance-any-of", ",".join(signal_provenances)])
    return args


def run_learning_updates(action: str, event: str, ctx: dict, result: dict, capability_registry: dict) -> dict:
    learning: dict[str, object] = {}
    result_status = result.get("status", "warning")
    rc_action, out_action, err_action = run_python(CORE / "scripts" / "learning_update.py", *learning_args_for_context(action, event, ctx, result_status))
    learning["action"] = {
        "returncode": rc_action,
        "stdout": parse_json_output(out_action) or out_action,
        "stderr": err_action,
    }

    action_meta = action_capability_meta(action, capability_registry)
    skill_name = action_meta.get("preferredSkill")
    verification = result.get("verification", {}) if isinstance(result.get("verification"), dict) else {}
    verification_parsed = verification.get("parsed", {}) if isinstance(verification.get("parsed"), dict) else {}
    if action == "inspect-local-signal" and verification_parsed.get("status") == "ok":
        skill_name = "desktop-input"
    if skill_name:
        rc_skill, out_skill, err_skill = run_python(
            CORE / "scripts" / "learning_update.py",
            "--bucket", "skill",
            "--name", skill_name,
            "--result", "success" if result_status == "ok" else "failure",
            "--amount", "0.01",
            "--note", f"resident-{action}-{skill_name}-{result_status}",
        )
        learning["skill"] = {
            "name": skill_name,
            "returncode": rc_skill,
            "stdout": parse_json_output(out_skill) or out_skill,
            "stderr": err_skill,
        }
    return learning


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--action", required=True)
    parser.add_argument("--event", default="local-signal")
    parser.add_argument("--score", type=float)
    args = parser.parse_args()

    action_state = load_optional_json(ACTION_STATE_PATH)
    resident_config = load_optional_json(RESIDENT_CONFIG_PATH)
    allow_resident_execution = action_state.get("allowResidentExecution", False)
    allowed_actions = action_state.get("residentAllowedActions", DEFAULT_ALLOWED_ACTIONS)
    history_limit = int(action_state.get("residentHistoryLimit", 30))
    ctx = signal_context()
    capability_registry = load_capability_registry()
    capability_meta = action_capability_meta(args.action, capability_registry)

    intent = {
        "timestamp": now_iso(),
        "intent": args.action,
        "event": args.event,
        "score": args.score,
        "execute": bool(allow_resident_execution and args.action in allowed_actions),
        "safeReadOnly": capability_meta.get("safeReadOnly", True),
        "note": "resident-selected-top-action",
        "signalTypes": ctx.get("signalTypes", []),
        "signalProvenances": ctx.get("signalProvenances", []),
        "capabilityId": capability_meta.get("capabilityId"),
        "capabilityDomain": capability_meta.get("capabilityDomain"),
        "preferredSkill": capability_meta.get("preferredSkill"),
    }

    action_state.setdefault("recentIntents", []).append(intent)
    action_state["recentIntents"] = trim_list(action_state["recentIntents"], history_limit)

    if not allow_resident_execution:
        result = {
            "status": "skipped",
            "reason": "allowResidentExecution=false",
            "selectedAction": args.action,
            "timestamp": now_iso(),
        }
    elif args.action not in allowed_actions:
        result = {
            "status": "skipped",
            "reason": "action-not-in-residentAllowedActions",
            "selectedAction": args.action,
            "timestamp": now_iso(),
        }
    else:
        result = execute_action(args.action, args.score, resident_config, ctx, capability_registry)
        result["selectedAction"] = args.action
        result["timestamp"] = now_iso()
        result["learning"] = run_learning_updates(args.action, args.event, ctx, result, capability_registry)
        result["semanticWriteback"] = apply_semantic_writeback(args.action, result)
        generic_lifecycle = record_generic_action_lifecycle(args.action, ctx, result)
        if generic_lifecycle:
            result["taskLifecycle"] = generic_lifecycle

    result = attach_capability_metadata(result, args.action, capability_registry)

    if result.get("review"):
        action_state.setdefault("recentVerifications", []).append(
            {
                "timestamp": now_iso(),
                "selectedAction": args.action,
                "primarySignal": result["review"].get("primarySignal"),
                "summary": result["review"].get("summary"),
                "verification": result.get("verification") or result["review"].get("verification"),
            }
        )
        action_state["recentVerifications"] = trim_list(action_state["recentVerifications"], history_limit)

    result = sanitize_json_value(result)
    action_state = sanitize_json_value(action_state)
    action_state.setdefault("recentExecutions", []).append(result)
    action_state["recentExecutions"] = trim_list(action_state["recentExecutions"], history_limit)
    action_state["updatedAt"] = now_iso()
    save_json(ACTION_STATE_PATH, action_state)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
