from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"


def now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def now_iso() -> str:
    return now().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def recent_screen_burst(perception: dict, repeat_threshold: int) -> dict | None:
    recent_signals = perception.get("recentSignals") or []
    if not recent_signals:
        return None
    last = recent_signals[-1]
    if last.get("type") != "screen-changed":
        return None
    repeat_count = int(last.get("repeatCount", 1))
    if repeat_count < repeat_threshold:
        return None
    return {
        "repeatCount": repeat_count,
        "firstObservedAt": last.get("firstObservedAt") or last.get("capturedAt"),
        "lastObservedAt": last.get("lastObservedAt") or last.get("capturedAt"),
    }


def build_decision(preview: dict, perception: dict, max_age_minutes: int, repeat_threshold: int) -> dict:
    reasons: list[str] = []
    mode = preview.get("mode")
    evidence = preview.get("evidence") or {}

    updated_at = parse_iso(preview.get("updatedAt"))
    if updated_at is None:
        reasons.append("missing-or-invalid-updatedAt")
    elif updated_at < now() - timedelta(minutes=max_age_minutes):
        reasons.append("preview-too-old")

    interval_seconds = preview.get("intervalSeconds")
    if not isinstance(interval_seconds, int) or interval_seconds <= 0:
        reasons.append("missing-or-invalid-intervalSeconds")

    if mode == "emitted-dominant" and evidence.get("countSource") != "last-probe":
        reasons.append("emitted-advice-not-fresh")

    burst = recent_screen_burst(perception, repeat_threshold)
    if mode == "emitted-dominant" and burst is not None:
        reasons.append("screen-burst-guard")

    approved = not reasons
    return {
        "approved": approved,
        "reasons": reasons,
        "mode": mode,
        "preview": preview,
        "screenBurst": burst,
        "evaluatedAt": now_iso(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview-path", default="state/resident_cadence_advice.preview.json")
    parser.add_argument("--live-path")
    parser.add_argument("--report-path")
    parser.add_argument("--max-age-minutes", type=int, default=30)
    parser.add_argument("--screen-repeat-threshold", type=int, default=3)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    config = load_json(CORE / "resident-config.json")
    preview_path = ROOT / args.preview_path
    live_path = ROOT / (args.live_path or config.get("cadenceAdvicePath", "state/resident_cadence_advice.json"))
    perception = load_json(CORE / "perception-state.json")
    allowed_apply_modes = config.get("applyCadenceAdviceModes", ["suppressed-dominant", "balanced-or-quiet"])

    if not preview_path.exists():
        result = {
            "approved": False,
            "reasons": ["preview-missing"],
            "previewPath": str(preview_path),
            "livePath": str(live_path),
            "evaluatedAt": now_iso(),
        }
    else:
        preview = load_json(preview_path)
        result = build_decision(preview, perception, args.max_age_minutes, args.screen_repeat_threshold)
        result["previewPath"] = str(preview_path)
        result["livePath"] = str(live_path)
        result["allowedApplyModes"] = allowed_apply_modes

        apply_eligible = result.get("approved") and result.get("mode") in allowed_apply_modes
        result["applyEligible"] = apply_eligible
        if args.apply and result.get("approved") and not apply_eligible:
            result.setdefault("reasons", []).append("mode-not-allowed-for-auto-apply")

        if args.apply and apply_eligible:
            save_json(live_path, preview)
            result["applied"] = True
        else:
            result["applied"] = False

    if args.report_path:
        save_json(ROOT / args.report_path, result)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
