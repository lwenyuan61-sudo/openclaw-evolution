from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
AUTO = ROOT / "autonomy"
STATE = ROOT / "state"
MEMORY_DIR = ROOT / "memory"
INSIGHT_STATE = STATE / "conversation_insights.json"
INBOX = STATE / "conversation_insight_inbox.jsonl"
OWNER_STATE = STATE / "owner_chat_signal_state.json"
GOAL_REGISTER = AUTO / "goal-register.json"
UPGRADE_STATE = AUTO / "upgrade-state.json"
LOG_PATH = AUTO / "experiment-log.jsonl"

KEYWORDS = [
    "Lee asked",
    "Lee said",
    "Lee wants",
    "Lee希望",
    "Lee 问",
    "Lee asked whether",
    "world-model",
    "world model",
    "世界模型",
    "预测层",
    "持续循环",
    "自我进化",
    "继续升级",
    "有效信息",
    "对话",
    "conversation",
    "future upgrade",
    "升级计划",
    "memory",
    "agent memory",
    "write-manage-read",
    "记忆",
    "摄取",
    "召回",
    "owner-chat-signal",
    "Lee said:",
    "复杂信息",
    "语义层",
    "神经网络",
    "候选生成",
]

MEMORY_LOOP_SOURCE = {
    "source": "arXiv:2603.07670 Memory for Autonomous LLM Agents: Mechanisms, Evaluation, and Emerging Frontiers",
    "url": "https://arxiv.org/abs/2603.07670",
    "principle": "Treat resident memory as a write-manage-read loop coupled to perception/action, not as an unstructured transcript dump.",
    "mechanismFamilies": [
        "context-resident compression",
        "retrieval-augmented stores",
        "reflective self-improvement",
        "hierarchical virtual context",
        "policy-learned management",
    ],
    "engineeringGates": [
        "write-path filtering",
        "deduplication and contradiction handling",
        "latency/noise budget",
        "privacy governance",
        "goal/action coupling verification",
    ],
}


def now_dt() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now_dt().isoformat(timespec="seconds")


def parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:
        return None


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default or {})
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def tail_jsonl(path: Path, limit: int = 80) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            if isinstance(item, dict):
                rows.append(item)
        except Exception:
            rows.append({"text": line[:500], "source": str(path)})
    return rows


def split_memory_blocks(text: str) -> list[str]:
    chunks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and current:
            chunks.append("\n".join(current).strip())
            current = [line]
        else:
            current.append(line)
    if current:
        chunks.append("\n".join(current).strip())
    return [c for c in chunks if c]


def normalize_id(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def extract_from_memory() -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    today_path = MEMORY_DIR / f"{now_dt().date().isoformat()}.md"
    paths = [today_path]
    # Include the newest daily note too, in case the local date changed or the
    # current session wrote to a previous day file.
    if MEMORY_DIR.exists():
        recent = sorted(MEMORY_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)[:2]
        for path in recent:
            if path not in paths:
                paths.append(path)
    for path in paths:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for block in split_memory_blocks(text):
            if not any(k.lower() in block.lower() for k in KEYWORDS):
                continue
            summary = re.sub(r"\s+", " ", block).strip()[:700]
            insights.append({
                "id": "memory-" + normalize_id(str(path) + summary),
                "source": str(path.relative_to(ROOT)),
                "kind": "daily-memory-conversation-signal",
                "summary": summary,
                "leeValue": 0.85,
                "upgradeRelevance": 0.8,
            })
    return insights


def extract_from_inbox() -> list[dict[str, Any]]:
    insights: list[dict[str, Any]] = []
    for item in tail_jsonl(INBOX):
        text = str(item.get("text") or item.get("summary") or "").strip()
        if not text:
            continue
        if not any(k.lower() in text.lower() for k in KEYWORDS):
            continue
        insights.append({
            "id": "inbox-" + normalize_id(json.dumps(item, ensure_ascii=False, sort_keys=True)),
            "source": str(INBOX.relative_to(ROOT)),
            "kind": "conversation-insight-inbox",
            "summary": text[:700],
            "leeValue": float(item.get("leeValue", 0.9) or 0.9),
            "upgradeRelevance": float(item.get("upgradeRelevance", 0.9) or 0.9),
        })
    return insights


def latest_owner_chat_signal_from_inbox() -> dict[str, Any] | None:
    latest: dict[str, Any] | None = None
    latest_dt: datetime | None = None
    for item in tail_jsonl(INBOX, limit=300):
        if not isinstance(item, dict):
            continue
        source = str(item.get("source") or "").lower()
        kind = str(item.get("kind") or "").lower()
        text = str(item.get("text") or item.get("summary") or "")
        is_owner_signal = kind == "owner-chat-signal" or source.startswith("owner-chat") or source.startswith("lee-") or text.startswith("Lee said:")
        if not is_owner_signal:
            continue
        item_dt = parse_dt(item.get("timestamp"))
        if item_dt is None:
            continue
        if latest_dt is None or item_dt > latest_dt:
            latest = item
            latest_dt = item_dt
    return latest


def refresh_owner_chat_bridge(timestamp: str, upgrade: dict[str, Any]) -> dict[str, Any]:
    owner_state = load_json(OWNER_STATE, {})
    latest = latest_owner_chat_signal_from_inbox()
    latest_dt = parse_dt(latest.get("timestamp")) if isinstance(latest, dict) else None
    current_dt = parse_dt(owner_state.get("lastIngestedAt"))
    refreshed = False
    if latest and latest_dt and (current_dt is None or latest_dt > current_dt or latest.get("id") != owner_state.get("lastSignalId")):
        owner_state = {
            "timestamp": timestamp,
            "lastIngestedAt": latest.get("timestamp"),
            "lastSignalId": latest.get("id") or "owner-chat-" + normalize_id(json.dumps(latest, ensure_ascii=False, sort_keys=True)),
            "lastIntents": latest.get("intents") or [],
            "inboxPath": str(INBOX.relative_to(ROOT)),
            "principle": "owner chat enters resident as bounded append-only summaries, then conversation_insight_tick/semantic_signal_layer decide how to use it",
            "refreshedBy": "conversation_insight_tick.ownerChatRuntimeAutoHook",
            "refreshedAt": timestamp,
        }
        save_json(OWNER_STATE, owner_state)
        cadence = upgrade.setdefault("internalizedCadence", {})
        if isinstance(cadence, dict):
            cadence["lastUserInteractionAt"] = latest.get("timestamp")
            cadence["lastOwnerChatSignalId"] = owner_state.get("lastSignalId")
            cadence["lastOwnerChatIntents"] = owner_state.get("lastIntents")
            cadence["lastOwnerChatIngestedAt"] = timestamp
            cadence["ownerChatBridge"] = "conversation_insight_tick auto-refreshes owner_chat_signal_state from bounded inbox"
        upgrade["lastOwnerChatSignal"] = {
            "id": owner_state.get("lastSignalId"),
            "timestamp": latest.get("timestamp"),
            "intents": owner_state.get("lastIntents"),
            "source": latest.get("source"),
            "messageId": latest.get("messageId"),
            "refreshedBy": "conversation_insight_tick",
        }
        refreshed = True
    last_dt = parse_dt(owner_state.get("lastIngestedAt"))
    stale_minutes = None
    if last_dt:
        stale_minutes = round((now_dt() - last_dt.astimezone()).total_seconds() / 60.0, 1)
    return {
        "enabled": True,
        "statePath": str(OWNER_STATE.relative_to(ROOT)),
        "lastOwnerChatSignalId": owner_state.get("lastSignalId"),
        "lastOwnerChatIngestedAt": owner_state.get("lastIngestedAt"),
        "latestInboxOwnerSignalId": latest.get("id") if latest else None,
        "latestInboxOwnerSignalAt": latest.get("timestamp") if latest else None,
        "refreshedOwnerState": refreshed,
        "staleMinutes": stale_minutes,
        "staleDespiteInbox": bool(latest_dt and last_dt and latest_dt > last_dt),
        "principle": "fresh owner intent can refresh resident routing from the bounded inbox without a manual memory flush",
    }


def ensure_goal(insights: list[dict[str, Any]], timestamp: str) -> list[str]:
    if not insights:
        return []
    register = load_json(GOAL_REGISTER, {})
    existing = {item.get("id") for item in register.get("candidates", []) if isinstance(item, dict)}
    generated: list[str] = []
    goal_id = "conversation-insight-ingestion-loop"
    if goal_id not in existing:
        register.setdefault("candidates", []).append({
            "id": goal_id,
            "title": "对话有效信息摄取与升级回路",
            "focus": "make Lee-assistant conversation insights enter resident autonomy instead of remaining only in chat context",
            "goal": "让the agent能把和 Lee 对话中的高价值想法、缺口、未来升级计划，转成状态、目标池、预测和验证任务",
            "subgoal": "建立 conversation text / daily-memory / insight-inbox -> conversation_insight_tick -> goal-register -> autonomy_upgrade_tick 的链路",
            "nextConcreteStep": "让 resident 定期运行 conversation_insight_tick.py，并把高价值对话洞察写入 state/conversation_insights.json 与 goal-register",
            "leeValue": 1.0,
            "continuityWeight": 0.98,
            "feasibility": 0.88,
            "learningLeverage": 1.0,
            "noiseRisk": 0.18,
            "relatedCapabilities": ["continuity-core", "initiative-control", "adaptive-learning", "world-modeling"],
            "status": "active",
            "source": "Lee-direction-conversation-gap",
            "createdAt": timestamp,
        })
        register["updatedAt"] = timestamp
        save_json(GOAL_REGISTER, register)
        generated.append(goal_id)
    return generated


def build_memory_control_loop(unique: list[dict[str, Any]], new_insights: list[dict[str, Any]], generated_goals: list[str], timestamp: str) -> dict[str, Any]:
    """Compile external memory-mechanism evidence into the existing resident memory path.

    The connector is deliberately state-level: it does not add a new memory
    subsystem.  It makes the current conversation/daily-memory ingestion path
    auditable as write -> manage -> read, so later resident ticks can see where
    evidence is filtered, deduplicated, routed into goals, and re-read by the
    autonomy selector.
    """
    write_sources = sorted({str(item.get("source")) for item in unique if item.get("source")})
    return {
        "enabled": True,
        "updatedAt": timestamp,
        "sourceEvidence": MEMORY_LOOP_SOURCE,
        "principle": "conversation memory must be filtered, managed, and selectively re-read before it can affect resident action",
        "write": {
            "sources": write_sources or ["memory/YYYY-MM-DD.md", "state/conversation_insight_inbox.jsonl"],
            "filters": ["keyword relevance", "non-empty summary", "stable hash id", "bounded source list"],
            "newInsightCount": len(new_insights),
            "totalInsightCount": len(unique),
        },
        "manage": {
            "dedupeKey": "sha256(source + normalized summary)",
            "seenSet": "state/conversation_insights.json.seenInsightIds[-500:]",
            "goalRouting": "ensure_goal() writes conversation-insight-ingestion-loop only when new evidence exists",
            "generatedGoalIds": generated_goals,
            "noiseControls": ["no live-chat scraping", "bounded recentInsights", "goal-register idempotence"],
        },
        "read": {
            "statePath": str(INSIGHT_STATE.relative_to(ROOT)),
            "upgradeHook": "autonomy/upgrade-state.json.conversationInsight.memoryControlLoop",
            "selectorHook": "goal-register -> autonomy_upgrade_tick.py",
            "residentUse": "future ticks can inspect memoryControlLoop before deciding whether conversation evidence is strong enough to affect action",
        },
        "coupling": {
            "perception": "daily-memory / insight-inbox are the current text perception inputs",
            "action": "goal-register and autonomy_upgrade_tick are the action-selection path",
            "knownGap": "live chat still enters this loop only when written into memory or insight inbox",
        },
    }


def main() -> None:
    timestamp = now_iso()
    previous = load_json(INSIGHT_STATE, {})
    upgrade = load_json(UPGRADE_STATE, {})
    owner_chat_bridge = refresh_owner_chat_bridge(timestamp, upgrade)
    seen = set(previous.get("seenInsightIds", []) or [])
    raw = extract_from_memory() + extract_from_inbox()
    unique: list[dict[str, Any]] = []
    for item in raw:
        if item["id"] not in {x["id"] for x in unique}:
            unique.append(item)
    new_insights = [item for item in unique if item.get("id") not in seen]
    generated_goals = ensure_goal(new_insights, timestamp)
    memory_control_loop = build_memory_control_loop(unique, new_insights, generated_goals, timestamp)

    state = {
        "timestamp": timestamp,
        "purpose": "capture high-value Lee conversation signals for resident autonomy and self-upgrade routing",
        "insightCount": len(unique),
        "newInsightCount": len(new_insights),
        "newInsights": new_insights[:10],
        "recentInsights": unique[-20:],
        "generatedGoalIds": generated_goals,
        "seenInsightIds": sorted(seen.union({item["id"] for item in unique}))[-500:],
        "sources": ["memory/YYYY-MM-DD.md", "state/conversation_insight_inbox.jsonl"],
        "limitation": "Resident cannot directly read arbitrary live chat transcript; owner-chat intent enters through owner_chat_signal_ingest or bounded inbox auto-refresh.",
        "ownerChatBridge": owner_chat_bridge,
        "memoryControlLoop": memory_control_loop,
    }
    save_json(INSIGHT_STATE, state)

    upgrade.setdefault("conversationInsight", {}).update({
        "enabled": True,
        "script": "core/scripts/conversation_insight_tick.py",
        "statePath": "state/conversation_insights.json",
        "memoryControlLoop": memory_control_loop,
        "lastRunAt": timestamp,
        "lastNewInsightCount": len(new_insights),
        "lastGeneratedGoalIds": generated_goals,
        "ownerChatBridge": owner_chat_bridge,
        "principle": "high-value conversation signals should enter resident goal routing, not remain only in chat context",
    })
    if new_insights or generated_goals or owner_chat_bridge.get("refreshedOwnerState"):
        internal = upgrade.setdefault("internalizedCadence", {})
        internal["forceUpgradeRequestedAt"] = timestamp
        internal["forceUpgradeReason"] = "owner-chat-bridge" if owner_chat_bridge.get("refreshedOwnerState") else "conversation-insight"
    upgrade["updatedAt"] = timestamp
    save_json(UPGRADE_STATE, upgrade)

    append_jsonl(LOG_PATH, {
        "id": "conversation-insight-" + timestamp,
        "timestamp": timestamp,
        "type": "conversation-insight",
        "status": "new-insights" if new_insights else "no-new-insights",
        "newInsightCount": len(new_insights),
        "generatedGoalIds": generated_goals,
        "ownerChatBridge": owner_chat_bridge,
    })
    print(json.dumps({
        "ok": True,
        "timestamp": timestamp,
        "insightCount": len(unique),
        "newInsightCount": len(new_insights),
        "generatedGoalIds": generated_goals,
        "ownerChatBridge": owner_chat_bridge,
        "statePath": str(INSIGHT_STATE),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
