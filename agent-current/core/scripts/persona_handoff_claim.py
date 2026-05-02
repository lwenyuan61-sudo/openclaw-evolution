from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_PATH = ROOT / "state" / "persona_deliberation_handoff.json"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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
    return (now() - dt).total_seconds() / 60.0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--claimed-by", default="the agent")
    parser.add_argument("--claim-id")
    parser.add_argument("--stale-minutes", type=float, default=20.0)
    parser.add_argument("--force-reclaim", action="store_true")
    args = parser.parse_args()

    handoff = load_optional_json(HANDOFF_PATH)
    timestamp = now_iso()

    if not handoff.get("pending"):
        print(json.dumps({
            "status": "skipped",
            "reason": "no-pending-persona-handoff",
            "timestamp": timestamp,
        }, ensure_ascii=False, indent=2))
        return

    if handoff.get("handledAt"):
        print(json.dumps({
            "status": "skipped",
            "reason": "handoff-already-handled",
            "timestamp": timestamp,
            "handledAt": handoff.get("handledAt"),
        }, ensure_ascii=False, indent=2))
        return

    existing_claim_id = handoff.get("claimId")
    claimed_at = handoff.get("claimedAt")
    elapsed = minutes_since(claimed_at)
    claim_active = bool(existing_claim_id and claimed_at and (elapsed is None or elapsed < float(args.stale_minutes)))

    if claim_active and not args.force_reclaim:
        print(json.dumps({
            "status": "skipped",
            "reason": "handoff-claim-still-active",
            "timestamp": timestamp,
            "claimId": existing_claim_id,
            "claimedAt": claimed_at,
            "claimedBy": handoff.get("claimedBy"),
            "elapsedMinutes": round(elapsed, 3) if elapsed is not None else None,
        }, ensure_ascii=False, indent=2))
        return

    claim_id = args.claim_id or f"claim-{now().strftime('%Y%m%dT%H%M%S')}"
    handoff["claimId"] = claim_id
    handoff["claimedAt"] = timestamp
    handoff["claimedBy"] = args.claimed_by
    handoff["claimCount"] = int(handoff.get("claimCount", 0) or 0) + 1
    handoff["lastClaimResult"] = {
        "status": "reclaimed" if existing_claim_id and args.force_reclaim else "claimed",
        "timestamp": timestamp,
        "claimId": claim_id,
        "claimedBy": args.claimed_by,
        "replacedClaimId": existing_claim_id if existing_claim_id != claim_id else None,
    }
    save_json(HANDOFF_PATH, handoff)

    print(json.dumps({
        "status": "ok",
        "timestamp": timestamp,
        "claimId": claim_id,
        "claimCount": handoff.get("claimCount"),
        "question": handoff.get("question"),
        "summary": handoff.get("summary"),
        "contextFiles": handoff.get("contextFiles"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
