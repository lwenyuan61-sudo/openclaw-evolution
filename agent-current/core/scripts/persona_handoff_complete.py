from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_PATH = ROOT / "state" / "persona_deliberation_handoff.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", required=True)
    parser.add_argument("--claimed-by", default="the agent")
    parser.add_argument("--claim-id")
    parser.add_argument("--allow-unclaimed", action="store_true")
    parser.add_argument("--reported-to-lee", action="store_true")
    parser.add_argument(
        "--visible-delivery-confirmed",
        action="store_true",
        help=(
            "Only set reportedToLee=true when the main persona has actually "
            "sent a visible user-facing message in the owner chat. Background "
            "workers/subagents must not use this as a substitute for delivery."
        ),
    )
    parser.add_argument("--lee-report-summary")
    args = parser.parse_args()

    handoff = load_optional_json(HANDOFF_PATH)
    timestamp = now_iso()

    if handoff.get("handledAt") and not handoff.get("pending"):
        print(json.dumps({
            "status": "skipped",
            "reason": "handoff-already-handled",
            "timestamp": timestamp,
            "handledAt": handoff.get("handledAt"),
        }, ensure_ascii=False, indent=2))
        return

    existing_claim_id = handoff.get("claimId")
    effective_claim_id = args.claim_id or existing_claim_id

    if existing_claim_id and args.claim_id and args.claim_id != existing_claim_id:
        print(json.dumps({
            "status": "error",
            "reason": "claim-id-mismatch",
            "timestamp": timestamp,
            "expectedClaimId": existing_claim_id,
            "providedClaimId": args.claim_id,
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    if not effective_claim_id and not args.allow_unclaimed:
        print(json.dumps({
            "status": "error",
            "reason": "missing-claim-id",
            "timestamp": timestamp,
        }, ensure_ascii=False, indent=2))
        sys.exit(2)

    handoff["pending"] = False
    handoff["claimedAt"] = handoff.get("claimedAt") or timestamp
    handoff["claimedBy"] = handoff.get("claimedBy") or args.claimed_by
    handoff["claimId"] = effective_claim_id
    handoff["handledAt"] = timestamp
    handoff["handledSummary"] = args.summary
    handoff["completedFromClaimId"] = effective_claim_id
    if args.reported_to_lee and args.visible_delivery_confirmed:
        # Tool-side code cannot observe whether the assistant's final message
        # was actually delivered to Lee. Earlier versions let this flag mark
        # reportedToLee=true, which created false positives: state said
        # “reported”, while Lee saw nothing. Treat this as an intent/prepared
        # marker only; the visible chat message itself is the delivery.
        handoff["reportedToLee"] = False
        handoff["reportPreparedForLee"] = True
        handoff["reportPreparedAt"] = timestamp
        handoff["leeReportSummary"] = args.lee_report_summary or handoff.get("leeReportSummary") or args.summary
        handoff["visibleDeliveryIntendedAt"] = timestamp
        handoff["visibleDeliveryRequired"] = True
        handoff["visibleDeliveryPolicy"] = "assistant-final-message-is-the-only-visible-delivery"
        handoff["deliveryState"] = "prepared-not-runtime-confirmed"
    elif args.reported_to_lee:
        # A background worker can prepare or recommend a report, but it cannot
        # truthfully mark delivery complete. The actual user-visible assistant
        # message is produced by the main persona after the handoff wakes it.
        handoff["reportedToLee"] = False
        handoff["reportPreparedForLee"] = True
        handoff["reportPreparedAt"] = timestamp
        handoff["leeReportSummary"] = args.lee_report_summary or handoff.get("leeReportSummary") or args.summary
        handoff["visibleDeliveryRequired"] = True
        handoff["visibleDeliveryPolicy"] = "main-persona-visible-message-required"
    handoff["lastCompletionResult"] = {
        "status": "completed",
        "timestamp": timestamp,
        "claimedBy": handoff.get("claimedBy"),
        "claimId": effective_claim_id,
        "reportedToLee": False,
        "visibleDeliveryConfirmed": False,
        "deliveryState": handoff.get("deliveryState"),
    }
    save_json(HANDOFF_PATH, handoff)

    print(json.dumps({
        "status": "ok",
        "timestamp": timestamp,
        "pending": False,
        "claimId": effective_claim_id,
        "reportedToLee": False,
        "visibleDeliveryConfirmed": False,
        "deliveryState": handoff.get("deliveryState"),
        "handledSummary": args.summary,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
