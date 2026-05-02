from __future__ import annotations

import json
import hashlib
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"

DELIBERATION_PATH = CORE / "deliberation-state.json"
SELF_STATE_PATH = CORE / "self-state.json"
CONTINUITY_PATH = AUTO / "continuity-state.json"
SELF_DIRECTION_PATH = AUTO / "self-direction-state.json"
ATTENTION_PATH = CORE / "attention-state.json"
LEARNING_PATH = CORE / "learning-state.json"
PROCEDURAL_PATH = CORE / "procedural-memory.json"
OPPORTUNITY_PATH = STATE / "lee_opportunity_review.json"
REFLECTION_PATH = STATE / "resident_reflection.json"
SIGNAL_REVIEW_PATH = STATE / "resident_signal_review.json"
EPISODE_PATH = STATE / "deliberation_episode.json"
SCREEN_TRIAGE_PATH = STATE / "deliberation_screen_state.json"
PERSONA_HANDOFF_PATH = STATE / "persona_deliberation_handoff.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def trim_list(items: list[dict], limit: int) -> list[dict]:
    if len(items) <= limit:
        return items
    return items[-limit:]


def ensure_list(value) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


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


def recommendation_fingerprint(recommendation: dict) -> str:
    primary = recommendation.get("primarySignal", {}) if isinstance(recommendation.get("primarySignal"), dict) else {}
    payload = {
        "reason": recommendation.get("reason"),
        "targetLayer": recommendation.get("targetLayer"),
        "capturedAt": primary.get("capturedAt"),
        "type": primary.get("type"),
        "provenance": primary.get("provenance"),
        "path": primary.get("path"),
        "oldHash": primary.get("oldHash"),
        "newHash": primary.get("newHash"),
        "oldContentHash": primary.get("oldContentHash"),
        "newContentHash": primary.get("newContentHash"),
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_question(primary: dict, recommendation: dict) -> str:
    signal_type = primary.get("type", "local-signal")
    provenance = primary.get("provenance", "unknown-provenance")
    if signal_type == "workspace-changed":
        path = primary.get("path", "unknown-path")
        return (
            f"对于这个已验证的 {provenance} {signal_type}（{path}），是否应该把它视为值得继续分析的文本/artifact 变化，"
            f"先在 S2 判断其价值与含义，再决定是否需要来问 Lee？"
        )
    return (
        f"对于这个已验证的 {provenance} {signal_type}，是否应该继续停留在内部低成本处理，"
        f"还是确认它值得触发 Lee-facing opportunity / 进一步编译成更低成本默认路由？"
    )


def build_hypotheses(primary: dict, opportunity_decision: dict) -> list[str]:
    signal_type = primary.get("type", "local-signal")
    provenance = primary.get("provenance", "unknown-provenance")
    if signal_type == "workspace-changed":
        path = primary.get("path", "unknown-path")
        return [
            f"这次 {provenance} {signal_type}（{path}）只是普通 artifact 变动，应保留为候选但不打扰 Lee",
            f"这次 {provenance} {signal_type}（{path}）带有值得继续分析的文本价值，应先进入 S2，再决定是否要问 Lee",
            f"这次 {provenance} {signal_type}（{path}）证据仍不足，应先继续内部观察与压缩证据",
        ]
    return [
        f"这次 {provenance} {signal_type} 只是一次性外部变化，应验证后回落到 S1，不打扰 Lee",
        f"这次 {provenance} {signal_type} 已经足够稳定，可确认 Lee-facing opportunity judgment",
        "这次证据仍不足，应结束 S2 episode 并把结果留作以后校准阈值的样本",
    ]


def tool_call(name: str, script: Path, *args: str) -> dict:
    rc, stdout, stderr = run_python(script, *args)
    return {
        "name": name,
        "returncode": rc,
        "stdout": stdout,
        "stderr": stderr,
        "parsed": parse_json_output(stdout),
        "ok": rc == 0,
    }


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


def direct_tool_call(name: str, payload: dict, *, ok: bool = True) -> dict:
    return {
        "name": name,
        "returncode": 0 if ok else 1,
        "stdout": json.dumps(payload, ensure_ascii=False, indent=2),
        "stderr": "",
        "parsed": payload,
        "ok": ok,
    }


def workspace_artifact_tool_call(primary: dict) -> dict:
    rel_path = primary.get("path")
    if not rel_path:
        return direct_tool_call("workspace-artifact-verify", {"reason": "missing-workspace-path"}, ok=False)

    target = ROOT / Path(rel_path)
    exists = target.exists() and target.is_file()
    observed_hash = file_sha256(target) if exists else None
    preview_available, preview, line_count = read_text_preview(target) if exists else (False, None, None)
    hash_matches_signal = bool(primary.get("newContentHash") and observed_hash == primary.get("newContentHash")) if exists else False
    payload = {
        "path": rel_path,
        "exists": exists,
        "observedContentHash": observed_hash,
        "contentHashMatchesSignal": hash_matches_signal,
        "contentPreviewAvailable": preview_available,
        "contentPreview": preview,
        "lineCount": line_count,
        "artifactDiffAvailable": bool(primary.get("artifactDiffAvailable")),
        "artifactKind": primary.get("artifactKind"),
        "signalType": primary.get("type"),
        "provenance": primary.get("provenance"),
    }
    return direct_tool_call("workspace-artifact-verify", payload, ok=bool(exists and (primary.get("newContentHash") is None or hash_matches_signal)))


def build_lee_report_recommendation(primary: dict, semantic_assessment: dict | None, opportunity_decision: dict, *, verified: bool, confirmed_opportunity: bool, outcome: str) -> dict:
    semantic = semantic_assessment if isinstance(semantic_assessment, dict) else {}
    signal_type = primary.get("type") if isinstance(primary, dict) else None
    provenance = primary.get("provenance") if isinstance(primary, dict) else None
    path = primary.get("path") if isinstance(primary, dict) else None
    should_handoff = bool(opportunity_decision.get("shouldHandoff")) if isinstance(opportunity_decision, dict) else False
    user_value = semantic.get("userValueLikelihood")
    semantic_attention = semantic.get("recommendedAttention")
    artifact_diff = bool(semantic.get("artifactDiffAvailable"))

    should_report = False
    reason = "no-report-worthy-thought"
    summary = None

    if (
        verified
        and signal_type == "workspace-changed"
        and provenance == "user-change"
        and (confirmed_opportunity or artifact_diff or semantic_attention in {"investigate", "handoff"})
        and user_value in {"medium", "high"}
    ):
        should_report = True
        reason = "valuable-text-artifact-thought-completed"
        summary = (
            f"我刚对 {path or 'workspace artifact'} 完成了一次受限 S2 分析，当前判断它不只是普通文件变动，"
            f"而是带有值得向 Lee 汇报的文本/artifact 价值；下一步应由本人格决定是否直接向 Lee 汇报结论或继续追问。"
        )
    elif verified and confirmed_opportunity and should_handoff:
        should_report = True
        reason = "confirmed-opportunity-should-be-surfaced-to-lee"
        summary = "我刚完成了一次有 Lee-facing 价值的受限 S2 判断，应该由本人格继续接手并向 Lee 汇报。"

    return {
        "shouldReportToLee": should_report,
        "reason": reason,
        "summary": summary,
        "outcome": outcome,
        "primarySignal": primary or None,
    }


def find_deliberation_pattern(procedural_memory: dict, primary: dict, capability_id: str | None) -> dict | None:
    patterns = list(procedural_memory.get("deliberationPatterns", []) or [])
    for pattern in patterns:
        conditions = pattern.get("conditions", {}) if isinstance(pattern.get("conditions"), dict) else {}
        signal_types = set(conditions.get("signalTypesAnyOf", []))
        provenances = set(conditions.get("signalProvenanceAnyOf", []))
        if signal_types and primary.get("type") not in signal_types:
            continue
        if provenances and primary.get("provenance") not in provenances:
            continue
        if conditions.get("workspacePath") and conditions.get("workspacePath") != primary.get("path"):
            continue
        if conditions.get("latestCapabilityId") and conditions.get("latestCapabilityId") != capability_id:
            continue
        return pattern
    return None


def upsert_deliberation_pattern(procedural_memory: dict, primary: dict, capability_id: str | None, capability_domain: str | None, total_score: int, episode_id: str) -> tuple[str, bool]:
    patterns = procedural_memory.setdefault("deliberationPatterns", [])
    existing = find_deliberation_pattern(procedural_memory, primary, capability_id)
    timestamp = now_iso()

    if existing:
        stats = existing.setdefault("stats", {})
        stats["success"] = int(stats.get("success", 0) or 0) + 1
        stats["verified"] = int(stats.get("verified", 0) or 0) + 1
        stats["lastEpisodeId"] = episode_id
        stats["lastTotalScore"] = total_score
        stats["updatedAt"] = timestamp
        existing.setdefault("episodeIds", []).append(episode_id)
        existing["episodeIds"] = list(dict.fromkeys(existing.get("episodeIds", [])))[-12:]
        return str(existing.get("id")), False

    pattern_id = f"deliberation-{primary.get('type', 'signal')}-{primary.get('provenance', 'unknown')}"
    patterns.append({
        "id": pattern_id,
        "preferredLayer": "S2-deliberation",
        "reason": "compiled-from-verified-s2-episode",
        "preferredOutcome": "confirm-opportunity-before-surfacing",
        "conditions": {
            "signalTypesAnyOf": [primary.get("type")] if primary.get("type") else [],
            "signalProvenanceAnyOf": [primary.get("provenance")] if primary.get("provenance") else [],
            "workspacePath": primary.get("path") if primary.get("type") == "workspace-changed" else None,
            "latestCapabilityId": capability_id,
            "latestCapabilityDomain": capability_domain,
            "minValueScore": total_score,
        },
        "source": "deliberation_episode",
        "episodeIds": [episode_id],
        "stats": {
            "success": 1,
            "verified": 1,
            "lastEpisodeId": episode_id,
            "lastTotalScore": total_score,
            "updatedAt": timestamp,
        },
    })
    return pattern_id, True


def apply_learning_writeback(learning_state: dict, verified: bool, surfaced: bool, compiled_new_pattern: bool, recommendation_reason: str | None) -> dict:
    counters = learning_state.setdefault("counters", {})
    weights = learning_state.setdefault("weights", {})
    event_weights = weights.setdefault("eventPriority", {})
    action_weights = weights.setdefault("actionPriority", {})
    updates: list[dict] = []

    counters["deliberationEpisodesRun"] = int(counters.get("deliberationEpisodesRun", 0) or 0) + 1
    if verified:
        counters["deliberationEpisodesVerified"] = int(counters.get("deliberationEpisodesVerified", 0) or 0) + 1
    if surfaced:
        counters["deliberationEpisodesSurfaced"] = int(counters.get("deliberationEpisodesSurfaced", 0) or 0) + 1
    if compiled_new_pattern:
        counters["deliberationPatternsCompiled"] = int(counters.get("deliberationPatternsCompiled", 0) or 0) + 1

    if verified:
        old_event = float(event_weights.get("local-signal", 1.0))
        new_event = round(clamp(old_event + 0.02, 0.6, 2.0), 3)
        event_weights["local-signal"] = new_event
        updates.append({"bucket": "eventPriority", "name": "local-signal", "old": old_event, "new": new_event})

        old_action = float(action_weights.get("inspect-local-signal", 0.85))
        new_action = round(clamp(old_action + 0.02, 0.3, 3.2), 3)
        action_weights["inspect-local-signal"] = new_action
        updates.append({"bucket": "actionPriority", "name": "inspect-local-signal", "old": old_action, "new": new_action})

    recommendation_log = ensure_list(learning_state.get("recentRecommendations"))
    recommendation_log.append({
        "timestamp": now_iso(),
        "type": "deliberation-episode",
        "reason": recommendation_reason,
        "verified": verified,
        "surfaced": surfaced,
        "compiledNewPattern": compiled_new_pattern,
    })
    learning_state["recentRecommendations"] = trim_list(list(recommendation_log), 20)

    observations = ensure_list(learning_state.get("deliberationWritebacks"))
    observations.append({
        "timestamp": now_iso(),
        "type": "deliberation-writeback",
        "summary": "verified S2 triage now writes back into procedural and learning layers",
        "verified": verified,
        "surfaced": surfaced,
    })
    learning_state["deliberationWritebacks"] = trim_list(list(observations), 20)

    weight_updates = ensure_list(learning_state.get("weightUpdates"))
    weight_updates.extend(updates)
    learning_state["weightUpdates"] = trim_list(list(weight_updates), 40)
    learning_state["updatedAt"] = now_iso()
    return {"updates": updates, "verified": verified, "surfaced": surfaced, "compiledNewPattern": compiled_new_pattern}


def write_persona_handoff(*, pending: bool, episode_id: str | None, recommendation: dict, self_state: dict, opportunity_decision: dict, confirmed_opportunity: bool, primary: dict, timestamp: str, outcome: str | None, active_capability_ids: list[str], semantic_assessment: dict | None = None) -> dict:
    existing = load_optional_json(PERSONA_HANDOFF_PATH)
    handoff = existing if isinstance(existing, dict) else {}
    if pending:
        handoff["handoffId"] = f"handoff-{episode_id}" if episode_id else handoff.get("handoffId")
        handoff["wakeRequestedAt"] = None
        handoff["wakeRequestCount"] = 0
        handoff["lastWakeMode"] = None
        handoff["lastWakeEventText"] = None
        handoff["lastWakeResult"] = None
        handoff["claimedAt"] = None
        handoff["claimedBy"] = None
        handoff["claimId"] = None
        handoff["claimCount"] = 0
        handoff["lastClaimResult"] = None
        handoff["handledAt"] = None
        handoff["handledSummary"] = None
        handoff["completedFromClaimId"] = None
        handoff["lastCompletionResult"] = None
        handoff["reportedToLee"] = False
        handoff["reportedToLeeAt"] = None
        handoff["leeReportSummary"] = None
    handoff.update({
        "pending": pending,
        "source": "deliberation-episode" if episode_id else handoff.get("source"),
        "episodeId": episode_id,
        "currentTrackId": self_state.get("currentTrackId"),
        "reason": recommendation.get("reason"),
        "question": build_question(primary, recommendation) if primary else None,
        "summary": (
            "一次已验证外部信号经过自动 S2 triage 后，已经被判断为值得由the agent本人格继续接手的高价值内部任务"
            if pending
            else handoff.get("summary")
        ),
        "semanticAssessment": semantic_assessment or handoff.get("semanticAssessment"),
        "nextActionHint": (
            "先 claim 这个 handoff，再读取 contextFiles，在当前人格连续性里完成判断/推进，最后回写 handledSummary"
            if pending
            else handoff.get("nextActionHint")
        ),
        "resumeChecklist": [
            "读取 state/persona_deliberation_handoff.json",
            "读取 contextFiles 中列出的状态文件",
            "如尚未 claim，则运行 core/scripts/persona_handoff_claim.py",
            "以当前人格连续性继续处理问题，而不是重新开新任务",
            "完成后运行 core/scripts/persona_handoff_complete.py 写回 handled 状态",
        ],
        "activeCapabilityIds": list(active_capability_ids or []),
        "contextFiles": [
            "core/self-state.json",
            "autonomy/continuity-state.json",
            "core/attention-state.json",
            "core/deliberation-state.json",
            "state/lee_opportunity_review.json",
            "state/resident_signal_review.json",
        ],
        "createdAt": timestamp if pending else handoff.get("createdAt"),
        "opportunityDecision": {
            **opportunity_decision,
            "confirmedByDeliberation": confirmed_opportunity,
            "deliberationOutcome": outcome,
        } if isinstance(opportunity_decision, dict) else None,
        "primarySignal": primary or None,
    })
    if primary.get("type") == "workspace-changed" and primary.get("path"):
        handoff["contextFiles"] = list(dict.fromkeys(list(handoff.get("contextFiles", [])) + [str(primary.get("path"))]))
    save_json(PERSONA_HANDOFF_PATH, handoff)
    return handoff


def main() -> None:
    deliberation = load_optional_json(DELIBERATION_PATH)
    recommendation = deliberation.get("lastRecommendation", {}) if isinstance(deliberation.get("lastRecommendation"), dict) else {}
    if not recommendation.get("recommended"):
        existing = load_optional_json(EPISODE_PATH)
        result = {
            "status": "skipped",
            "reason": "no-active-deliberation-recommendation",
            "timestamp": now_iso(),
            "lastCompletedEpisodeId": existing.get("lastCompletedEpisodeId") or existing.get("episodeId") if isinstance(existing, dict) else None,
            "lastCompletedOutcome": existing.get("lastCompletedOutcome") or existing.get("outcome") if isinstance(existing, dict) else None,
        }
        save_json(EPISODE_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    fingerprint = recommendation_fingerprint(recommendation)
    last_episode = deliberation.get("lastEpisode", {}) if isinstance(deliberation.get("lastEpisode"), dict) else {}
    if last_episode.get("recommendationFingerprint") == fingerprint:
        existing = load_optional_json(EPISODE_PATH)
        result = {
            "status": "skipped",
            "reason": "recommendation-already-handled",
            "timestamp": now_iso(),
            "episodeId": last_episode.get("episodeId"),
            "recommendationFingerprint": fingerprint,
            "lastCompletedEpisodeId": (existing.get("lastCompletedEpisodeId") or existing.get("episodeId")) if isinstance(existing, dict) else last_episode.get("episodeId"),
            "lastCompletedOutcome": (existing.get("lastCompletedOutcome") or existing.get("outcome")) if isinstance(existing, dict) else last_episode.get("outcome"),
        }
        save_json(EPISODE_PATH, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    self_state = load_optional_json(SELF_STATE_PATH)
    continuity = load_optional_json(CONTINUITY_PATH)
    self_direction = load_optional_json(SELF_DIRECTION_PATH)
    attention = load_optional_json(ATTENTION_PATH)
    learning_state = load_optional_json(LEARNING_PATH)
    procedural_memory = load_optional_json(PROCEDURAL_PATH)
    opportunity_review = load_optional_json(OPPORTUNITY_PATH)
    reflection = load_optional_json(REFLECTION_PATH)
    signal_review = load_optional_json(SIGNAL_REVIEW_PATH)
    persona_handoff = load_optional_json(PERSONA_HANDOFF_PATH)

    primary = recommendation.get("primarySignal", {}) if isinstance(recommendation.get("primarySignal"), dict) else {}
    episode_id = f"s2-{datetime.now(timezone.utc).astimezone().strftime('%Y%m%dT%H%M%S')}"
    started_at = now_iso()
    tool_budget = int(deliberation.get("toolBudget", {}).get("maxToolCallsPerEpisode", 6) or 6)
    tool_calls: list[dict] = []

    if primary.get("type") == "workspace-changed":
        if tool_budget >= 1:
            tool_calls.append(workspace_artifact_tool_call(primary))
    else:
        if tool_budget >= 1:
            tool_calls.append(tool_call(
                "screen-state-triage",
                ROOT / "skills" / "screen-state" / "scripts" / "screen_state.py",
                "--write-json", str(SCREEN_TRIAGE_PATH),
            ))
        if tool_budget >= 2:
            tool_calls.append(tool_call(
                "cursor-verify",
                CORE / "scripts" / "reality_action.py",
                "--intent", "inspect-cursor",
                "--execute",
                "--note", "deliberation-episode-verify-signal",
            ))

    tool_calls_used = len(tool_calls)
    tool_calls_ok = all(call.get("ok") for call in tool_calls)
    resident_verification = signal_review.get("verification", {}) if isinstance(signal_review.get("verification"), dict) else {}
    resident_verification_ok = resident_verification.get("status") == "ok" or resident_verification.get("parsed", {}).get("status") == "ok"
    latest_capability_id = signal_review.get("capabilityId") or reflection.get("latestCapabilityId")
    latest_capability_domain = signal_review.get("capabilityDomain") or reflection.get("latestCapabilityDomain")

    screen_probe = next((call for call in tool_calls if call.get("name") == "screen-state-triage"), None)
    screen_probe_parsed = screen_probe.get("parsed", {}) if isinstance(screen_probe, dict) and isinstance(screen_probe.get("parsed"), dict) else {}
    screen_hash_matches = bool(primary.get("newHash") and screen_probe_parsed.get("screenHash") == primary.get("newHash"))

    cursor_probe = next((call for call in tool_calls if call.get("name") == "cursor-verify"), None)
    cursor_probe_parsed = cursor_probe.get("parsed", {}) if isinstance(cursor_probe, dict) and isinstance(cursor_probe.get("parsed"), dict) else {}
    workspace_probe = next((call for call in tool_calls if call.get("name") == "workspace-artifact-verify"), None)
    workspace_probe_parsed = workspace_probe.get("parsed", {}) if isinstance(workspace_probe, dict) and isinstance(workspace_probe.get("parsed"), dict) else {}
    workspace_hash_matches = bool(workspace_probe_parsed.get("contentHashMatchesSignal"))

    total_score = int(reflection.get("totalScore", opportunity_review.get("totalScore", 0)) or 0)
    opportunity_decision = opportunity_review.get("decision", {}) if isinstance(opportunity_review.get("decision"), dict) else {}
    semantic_assessment = opportunity_review.get("semanticAssessment") if isinstance(opportunity_review.get("semanticAssessment"), dict) else reflection.get("semanticAssessment")
    verified = resident_verification_ok and tool_calls_ok
    confirmed_opportunity = bool(opportunity_decision.get("shouldSurface") and verified and total_score >= 8)
    persona_handoff_allowed = bool(opportunity_decision.get("shouldHandoff", opportunity_decision.get("shouldSurface")))

    outcome = "fallback-to-s1"
    result_text = "insufficient-evidence-returned-to-S1"
    if verified and confirmed_opportunity:
        outcome = "confirmed-opportunity-and-compiled-pattern"
        result_text = "confirmed-lee-opportunity-after-constrained-S2-triage"
    elif verified:
        outcome = "verified-and-compiled-pattern"
        result_text = "verified-signal-and-compiled-lower-cost-writeback"

    lee_report_recommendation = build_lee_report_recommendation(
        primary,
        semantic_assessment,
        opportunity_decision,
        verified=verified,
        confirmed_opportunity=confirmed_opportunity,
        outcome=outcome,
    )

    compiled_pattern_id = None
    compiled_new_pattern = False
    if verified and primary:
        compiled_pattern_id, compiled_new_pattern = upsert_deliberation_pattern(
            procedural_memory,
            primary,
            latest_capability_id,
            latest_capability_domain,
            total_score,
            episode_id,
        )
        procedural_memory["updatedAt"] = now_iso()

    learning_writeback = apply_learning_writeback(
        learning_state,
        verified=verified,
        surfaced=confirmed_opportunity,
        compiled_new_pattern=compiled_new_pattern,
        recommendation_reason=recommendation.get("reason"),
    )

    timestamp = now_iso()
    future_plan = "未来优先继续观察『语义解释 -> shouldSurface / shouldHandoff -> S2 / handoff』这条新链是否稳定减少误唤醒；如果稳定，再把相同语义判断方式扩到更多信号类型，而不是只围绕 screen-change。"
    self_state["lastAction"] = "resident 已把一次候选机会送入受预算约束的 S2 episode，并将验证结果连同语义判断一起写回 procedural / learning / opportunity / continuity 层"
    self_state["stopPoint"] = "现在系统不再只靠 recommendation 与硬阈值升级，而是会先形成 semanticAssessment，再决定 shouldSurface / shouldHandoff，并把 S2 结果压回低成本层"
    self_state["nextStep"] = future_plan
    self_state["currentLayer"] = "S1-procedural"
    self_state["updatedAt"] = timestamp
    self_state["lastMeaningfulProgressAt"] = timestamp

    continuity["lastAction"] = self_state.get("lastAction")
    continuity["currentStopPoint"] = self_state.get("stopPoint")
    continuity["nextLikelyStep"] = future_plan
    continuity["updatedAt"] = timestamp

    self_direction["lastS2EpisodeId"] = episode_id
    self_direction["lastS2Outcome"] = outcome
    self_direction["lastS2Verified"] = verified
    self_direction["lastS2CompiledPatternId"] = compiled_pattern_id
    self_direction["lastOpportunityDecision"] = {
        **opportunity_decision,
        "confirmedByDeliberation": confirmed_opportunity,
        "deliberationEpisodeId": episode_id,
    }
    self_direction["lastLeeReportRecommendation"] = lee_report_recommendation
    self_direction["updatedAt"] = timestamp

    attention["currentAttentionTarget"] = self_state.get("activeGoal") or attention.get("currentAttentionTarget")
    attention.setdefault("promotedEvents", []).append({
        "timestamp": timestamp,
        "type": "deliberation-episode",
        "episodeId": episode_id,
        "reason": recommendation.get("reason"),
        "outcome": outcome,
    })
    attention["promotedEvents"] = trim_list(list(attention.get("promotedEvents", [])), 20)
    attention["updatedAt"] = timestamp

    opportunity_review["timestamp"] = timestamp
    opportunity_review["currentTrackId"] = self_direction.get("currentTrackId")
    opportunity_review["decision"] = {
        **opportunity_decision,
        "confirmedByDeliberation": confirmed_opportunity,
        "deliberationEpisodeId": episode_id,
        "deliberationOutcome": outcome,
    }
    opportunity_review["leeReportRecommendation"] = lee_report_recommendation
    if semantic_assessment:
        opportunity_review["semanticAssessment"] = semantic_assessment
    opportunity_review["deliberationRecommendation"] = {
        **recommendation,
        "handled": True,
        "handledAt": timestamp,
        "handledByEpisodeId": episode_id,
    }
    opportunity_review["deliberationEpisode"] = {
        "episodeId": episode_id,
        "verified": verified,
        "toolCallsUsed": tool_calls_used,
        "screenHashMatches": screen_hash_matches,
        "workspaceHashMatches": workspace_hash_matches,
        "workspacePreview": workspace_probe_parsed.get("contentPreview"),
        "cursorPosition": cursor_probe_parsed.get("stdout"),
        "outcome": outcome,
    }
    if confirmed_opportunity:
        opportunity_review["lastConfirmedByDeliberation"] = {
            "episodeId": episode_id,
            "timestamp": timestamp,
            "primarySignal": primary or None,
            "outcome": outcome,
        }

    persona_handoff_required = bool(
        confirmed_opportunity
        and (persona_handoff_allowed or lee_report_recommendation.get("shouldReportToLee"))
        and deliberation.get("episodePolicy", {}).get("requireOpportunityEvidenceForPersonaHandoff", True)
    )
    persona_handoff = write_persona_handoff(
        pending=persona_handoff_required,
        episode_id=episode_id if persona_handoff_required else persona_handoff.get("episodeId"),
        recommendation=recommendation,
        self_state=self_state,
        opportunity_decision=opportunity_decision,
        confirmed_opportunity=confirmed_opportunity,
        primary=primary,
        timestamp=timestamp,
        outcome=outcome,
        active_capability_ids=list(self_state.get("activeCapabilityIds", []) or []),
        semantic_assessment=semantic_assessment,
    )
    if lee_report_recommendation.get("shouldReportToLee"):
        persona_handoff["shouldReportToLee"] = True
        persona_handoff["leeReportRecommendation"] = lee_report_recommendation
        if persona_handoff_required:
            persona_handoff["summary"] = lee_report_recommendation.get("summary") or persona_handoff.get("summary")
            save_json(PERSONA_HANDOFF_PATH, persona_handoff)

    deliberation["status"] = "idle"
    deliberation["currentLayer"] = "S1-procedural"
    deliberation["lastRecommendation"] = {
        **recommendation,
        "handled": True,
        "handledAt": timestamp,
        "handledByEpisodeId": episode_id,
        "recommendationFingerprint": fingerprint,
    }
    episode_record = {
        "episodeId": episode_id,
        "trigger": recommendation.get("reason"),
        "question": build_question(primary, recommendation),
        "hypotheses": build_hypotheses(primary, opportunity_decision),
        "toolCallsUsed": tool_calls_used,
        "toolCalls": tool_calls,
        "verified": verified,
        "confirmedOpportunity": confirmed_opportunity,
        "screenHashMatches": screen_hash_matches,
        "workspaceHashMatches": workspace_hash_matches,
        "cursorPosition": cursor_probe_parsed.get("stdout"),
        "workspacePreview": workspace_probe_parsed.get("contentPreview"),
        "result": result_text,
        "outcome": outcome,
        "compiledPatternId": compiled_pattern_id,
        "semanticAssessment": semantic_assessment,
        "leeReportRecommendation": lee_report_recommendation,
        "learningWriteback": learning_writeback,
        "primarySignal": primary or None,
        "recommendationFingerprint": fingerprint,
        "startedAt": started_at,
        "endedAt": timestamp,
        "returnedToLayer": "S1-procedural",
    }
    deliberation["lastEpisode"] = episode_record
    deliberation.setdefault("recentEpisodes", []).append({
        "episodeId": episode_id,
        "trigger": recommendation.get("reason"),
        "verified": verified,
        "outcome": outcome,
        "compiledPatternId": compiled_pattern_id,
        "endedAt": timestamp,
    })
    deliberation["recentEpisodes"] = trim_list(list(deliberation.get("recentEpisodes", [])), 12)
    deliberation["updatedAt"] = timestamp

    save_json(DELIBERATION_PATH, deliberation)
    save_json(SELF_STATE_PATH, self_state)
    save_json(CONTINUITY_PATH, continuity)
    save_json(SELF_DIRECTION_PATH, self_direction)
    save_json(ATTENTION_PATH, attention)
    save_json(LEARNING_PATH, learning_state)
    save_json(PROCEDURAL_PATH, procedural_memory)
    save_json(OPPORTUNITY_PATH, opportunity_review)

    result = {
        "status": "ok",
        "timestamp": timestamp,
        "episodeId": episode_id,
        "verified": verified,
        "confirmedOpportunity": confirmed_opportunity,
        "compiledPatternId": compiled_pattern_id,
        "compiledNewPattern": compiled_new_pattern,
        "screenHashMatches": screen_hash_matches,
        "toolCallsUsed": tool_calls_used,
        "outcome": outcome,
        "result": result_text,
        "learningWriteback": learning_writeback,
        "personaHandoffPending": bool(persona_handoff.get("pending")),
        "lastCompletedEpisodeId": episode_id,
        "lastCompletedOutcome": outcome,
    }
    save_json(EPISODE_PATH, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
