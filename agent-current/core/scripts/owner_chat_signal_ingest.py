from __future__ import annotations

import argparse
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
STATE = ROOT / "state"
INBOX = STATE / "conversation_insight_inbox.jsonl"
OWNER_STATE = STATE / "owner_chat_signal_state.json"
LOG_PATH = ROOT / "autonomy" / "experiment-log.jsonl"
UPGRADE_PATH = ROOT / "autonomy" / "upgrade-state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def signal_id(text: str, source: str, message_id: str | None) -> str:
    raw = json.dumps({"text": normalize_text(text), "source": source, "messageId": message_id}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def classify(text: str) -> dict[str, Any]:
    lower = text.lower()
    intents: list[str] = []
    if any(k in text for k in ["自主", "进化", "升级", "resident", "候选", "信号", "语义", "神经网络"]):
        intents.append("autonomy-upgrade")
    if any(k in text for k in ["记住", "memory", "长期", "偏好"]):
        intents.append("memory-preference")
    if any(k in text for k in ["可以", "ok", "按", "做", "落实", "继续"]):
        intents.append("authorization-or-continuation")
    if any(k in text for k in ["为什么", "是不是", "怎么样", "什么情况", "能力"]):
        intents.append("diagnostic-question")
    if not intents:
        intents.append("owner-message")
    lee_value = 1.0 if "autonomy-upgrade" in intents or "authorization-or-continuation" in intents else 0.85
    upgrade_relevance = 1.0 if any(i in intents for i in ["autonomy-upgrade", "diagnostic-question"]) else 0.75
    return {"intents": intents, "leeValue": lee_value, "upgradeRelevance": upgrade_relevance}


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default or {})
    except Exception:
        return dict(default or {})


def inbox_has_signal(signal_id_value: str) -> bool:
    if not INBOX.exists():
        return False
    try:
        # Bounded tail scan: enough for repeated runtime retries without turning
        # the append-only inbox into an expensive full-history read.
        lines = INBOX.read_text(encoding="utf-8", errors="replace").splitlines()[-500:]
    except Exception:
        return False
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        if isinstance(item, dict) and item.get("id") == signal_id_value:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Safely append an owner-chat message summary into the resident conversation insight inbox.")
    parser.add_argument("--text", required=True)
    parser.add_argument("--source", default="owner-chat")
    parser.add_argument("--message-id")
    parser.add_argument("--timestamp")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    text = normalize_text(args.text)
    if not text:
        raise SystemExit("empty --text")
    clipped = text[:2000]
    classified = classify(clipped)
    ts = args.timestamp or now_iso()
    item = {
        "id": "owner-chat-" + signal_id(clipped, args.source, args.message_id),
        "timestamp": ts,
        "source": args.source,
        "messageId": args.message_id,
        "text": "Lee said: " + clipped,
        "kind": "owner-chat-signal",
        "intents": classified["intents"],
        "leeValue": classified["leeValue"],
        "upgradeRelevance": classified["upgradeRelevance"],
        "privacy": {
            "ownerChatOnly": True,
            "appendOnlyInbox": True,
            "noExternalWrite": True,
        },
    }
    result = {"ok": True, "dryRun": bool(args.dry_run), "item": item}
    duplicate = inbox_has_signal(item["id"])
    result["duplicate"] = duplicate
    if not args.dry_run and not duplicate:
        append_jsonl(INBOX, item)
        state = {
            "timestamp": now_iso(),
            "lastIngestedAt": ts,
            "lastSignalId": item["id"],
            "lastIntents": item["intents"],
            "inboxPath": str(INBOX.relative_to(ROOT)),
            "principle": "owner chat enters resident as bounded append-only summaries, then conversation_insight_tick/semantic_signal_layer decide how to use it",
        }
        save_json(OWNER_STATE, state)
        upgrade = load_json(UPGRADE_PATH, {})
        cadence = upgrade.setdefault("internalizedCadence", {})
        if isinstance(cadence, dict):
            cadence["lastUserInteractionAt"] = ts
            cadence["lastOwnerChatSignalId"] = item["id"]
            cadence["lastOwnerChatIntents"] = item["intents"]
            cadence["lastOwnerChatIngestedAt"] = now_iso()
            cadence["ownerChatBridge"] = "owner_chat_signal_ingest -> conversation_insight_inbox -> internalizedCadence"
        upgrade["lastOwnerChatSignal"] = {
            "id": item["id"],
            "timestamp": ts,
            "intents": item["intents"],
            "source": item["source"],
            "messageId": item.get("messageId"),
        }
        save_json(UPGRADE_PATH, upgrade)
        append_jsonl(LOG_PATH, {
            "id": "owner-chat-signal-ingest-" + ts,
            "timestamp": ts,
            "type": "owner-chat-signal-ingest",
            "status": "appended",
            "signalId": item["id"],
            "intents": item["intents"],
            "cadenceRefreshed": True,
        })
    elif not args.dry_run and duplicate:
        result["ok"] = True
        result["status"] = "duplicate-skipped"
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
