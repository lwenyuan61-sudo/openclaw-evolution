from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
CONFIG_PATH = CORE / "signal-probe-config.json"
ORGAN_LINK_GRAPH_PATH = STATE / "organ_link_graph.json"


def emit_json(payload: dict) -> None:
    """Emit UTF-8 JSON even when resident runs under a legacy Windows console codepage."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


DEFAULT_CONFIG = {
    "ignoreRoots": [".git", "__pycache__", "state"],
    "ignoreExactPaths": [
        "core/self-state.json",
        "core/attention-state.json",
        "core/homeostasis.json",
        "core/session-mode.json",
        "core/learning-state.json",
        "core/body-state.json",
        "core/perception-state.json",
        "core/action-state.json",
        "autonomy/continuity-state.json",
    ],
    "allowedSuffixes": [".md", ".json", ".py"],
    "internalPathPrefixes": [
        "core/",
        "autonomy/",
        "memory/",
        "state/",
        "cerebellum/",
        "skills/",
        "AGENTS.md",
        "AUTONOMY.md",
        "BACKLOG.md",
        "HEARTBEAT.md",
        "IDENTITY.md",
        "MEMORY.md",
        "SOUL.md",
        "TOOLS.md",
        "USER.md",
    ],
    "emitDeviceSnapshotOnlyOnSummaryChange": True,
    "emitSelfWriteWorkspaceSignals": False,
    "compressSignalHistory": True,
    "maxRecentSignals": 30,
    "maxRecentSuppressedSignals": 12,
    "maxWorkspaceArtifactSnapshots": 40,
    "signalSalience": {
        "workspace-changed": "low",
        "workspace-user-changed": "medium",
        "device-snapshot-present": "low",
        "screen-changed": "medium"
    },
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_optional_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_config() -> dict:
    config = json.loads(json.dumps(DEFAULT_CONFIG))
    if CONFIG_PATH.exists():
        user_config = load_json(CONFIG_PATH)
        for key, value in user_config.items():
            if isinstance(value, dict) and isinstance(config.get(key), dict):
                config[key].update(value)
            else:
                config[key] = value
    return config


def normalize_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def classify_workspace_provenance(rel: str, config: dict) -> str:
    internal_prefixes = config.get("internalPathPrefixes", [])
    for prefix in internal_prefixes:
        if prefix.endswith("/"):
            if rel.startswith(prefix):
                return "self-write"
        elif rel == prefix:
            return "self-write"
    return "user-change"


def latest_workspace_change(config: dict) -> dict | None:
    ignore_roots = set(config.get("ignoreRoots", []))
    ignore_exact = set(config.get("ignoreExactPaths", []))
    allowed_suffixes = {suffix.lower() for suffix in config.get("allowedSuffixes", [".md", ".json", ".py"])}

    latest = None
    latest_ts = None
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        rel = normalize_rel(p)
        parts = set(Path(rel).parts)
        if parts & ignore_roots:
            continue
        if rel in ignore_exact:
            continue
        if p.suffix.lower() not in allowed_suffixes:
            continue
        ts = p.stat().st_mtime
        if latest_ts is None or ts > latest_ts:
            latest_ts = ts
            latest = {
                "latestMtime": datetime.fromtimestamp(ts, tz=timezone.utc).astimezone().isoformat(timespec="seconds"),
                "path": rel,
                "provenance": classify_workspace_provenance(rel, config),
            }
    return latest


def summary_signature(value: dict) -> str:
    return json.dumps(value or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def compressible_signature(signal: dict) -> str:
    copy = {
        key: value
        for key, value in signal.items()
        if key not in {"capturedAt", "latestMtime", "oldHash", "newHash", "repeatCount", "firstObservedAt", "lastObservedAt"}
    }
    return json.dumps(copy, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def append_signal(history: list[dict], signal: dict, *, compress: bool) -> None:
    if not history:
        history.append(signal)
        return
    if not compress:
        history.append(signal)
        return

    current_sig = compressible_signature(signal)
    last = history[-1]
    if compressible_signature(last) != current_sig:
        history.append(signal)
        return

    repeat_count = int(last.get("repeatCount", 1)) + 1
    last["repeatCount"] = repeat_count
    last.setdefault("firstObservedAt", last.get("capturedAt") or last.get("latestMtime") or now_iso())
    last["lastObservedAt"] = signal.get("capturedAt") or signal.get("latestMtime") or now_iso()


def trim_history(history: list[dict], max_items: int) -> None:
    if len(history) > max_items:
        del history[:-max_items]


def workspace_artifact_kind(path: Path, text_readable: bool) -> str:
    suffix = path.suffix.lower()
    if suffix == ".md":
        return "markdown-note"
    if suffix == ".json":
        return "json-artifact"
    if suffix == ".py":
        return "python-source"
    if text_readable:
        return "text-artifact"
    return "binary-artifact"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def text_readable(path: Path) -> bool:
    try:
        with path.open("r", encoding="utf-8") as handle:
            handle.read(4096)
        return True
    except Exception:
        return False


def workspace_artifact_snapshot(path: Path) -> dict | None:
    if not path.exists() or not path.is_file():
        return None
    readable = text_readable(path)
    return {
        "contentHash": file_sha256(path),
        "sizeBytes": path.stat().st_size,
        "suffix": path.suffix.lower(),
        "textReadable": readable,
        "kind": workspace_artifact_kind(path, readable),
    }


def trim_snapshot_map(items: dict, max_items: int) -> dict:
    if len(items) <= max_items:
        return items
    trimmed = dict(items)
    while len(trimmed) > max_items:
        first = next(iter(trimmed))
        trimmed.pop(first, None)
    return trimmed


def organ_evidence(organ_link_graph: dict, ability_id: str) -> dict | None:
    """Return compact organ-link context to attach to raw signals.

    This keeps signal enrichment advisory/read-only: no tool execution, no
    external writes, and no behavior change outside downstream scoring that
    explicitly opts into the attached evidence.
    """
    bindings = organ_link_graph.get("bindings") if isinstance(organ_link_graph, dict) else []
    if not isinstance(bindings, list):
        return None
    binding = next((item for item in bindings if isinstance(item, dict) and item.get("abilityId") == ability_id), None)
    if not binding:
        return None
    runtime = binding.get("runtimeEvidence") if isinstance(binding.get("runtimeEvidence"), dict) else {}
    evidence = {
        "bindingId": binding.get("id"),
        "abilityId": binding.get("abilityId"),
        "organ": binding.get("organ"),
        "semanticLabels": list(runtime.get("semanticLabels", []) or [])[:8],
        "activeWindow": runtime.get("activeWindow") if isinstance(runtime.get("activeWindow"), dict) else None,
        "deviceSummary": runtime.get("deviceSummary") if isinstance(runtime.get("deviceSummary"), dict) else None,
        "source": "state/organ_link_graph.json.runtimeEvidence",
    }
    return {key: value for key, value in evidence.items() if value not in (None, [], {})}


def main() -> None:
    config = load_config()
    perception_path = CORE / "perception-state.json"
    screen_state_path = STATE / "screen_state.json"
    device_state_path = STATE / "device_state_snapshot.json"

    perception = load_json(perception_path)
    organ_link_graph = load_optional_json(ORGAN_LINK_GRAPH_PATH)
    signals: list[dict] = []
    suppressed_signals: list[dict] = []
    salience_map = config.get("signalSalience", {})
    compress_history = bool(config.get("compressSignalHistory", True))

    if screen_state_path.exists():
        screen = load_json(screen_state_path)
        current_hash = screen.get("screenHash")
        previous_hash = perception.get("lastScreenHash")
        if current_hash and previous_hash and current_hash != previous_hash:
            signal = {
                "type": "screen-changed",
                "capturedAt": screen.get("capturedAt"),
                "oldHash": previous_hash,
                "newHash": current_hash,
                "provenance": "real-desktop-change",
                "salience": salience_map.get("screen-changed", "medium"),
            }
            evidence = organ_evidence(organ_link_graph, "screen-observation")
            if evidence:
                signal["organEvidence"] = evidence
            signals.append(signal)
            counters = perception.setdefault("signalCounters", {})
            counters["screenChanged"] = counters.get("screenChanged", 0) + 1
        perception["lastScreenHash"] = current_hash
        perception["lastScreenCapturedAt"] = screen.get("capturedAt")

    if device_state_path.exists():
        device = load_json(device_state_path)
        current_summary = device.get("summary", {})
        current_signature = summary_signature(current_summary)
        previous_signature = perception.get("lastDeviceSummarySignature")
        should_emit = True
        if config.get("emitDeviceSnapshotOnlyOnSummaryChange", True) and current_signature == previous_signature:
            should_emit = False
        if should_emit:
            signal = {
                "type": "device-snapshot-present",
                "capturedAt": device.get("capturedAt"),
                "summary": current_summary,
                "provenance": "self-sensed",
                "salience": salience_map.get("device-snapshot-present", "low"),
            }
            evidence = organ_evidence(organ_link_graph, "device-sensing")
            if evidence:
                signal["organEvidence"] = evidence
            signals.append(signal)
            counters = perception.setdefault("signalCounters", {})
            counters["deviceSnapshotRefreshed"] = counters.get("deviceSnapshotRefreshed", 0) + 1
        perception["lastDeviceSummarySignature"] = current_signature
        perception["lastDeviceCapturedAt"] = device.get("capturedAt")

    latest_workspace = latest_workspace_change(config)
    if latest_workspace and latest_workspace.get("latestMtime") != perception.get("lastWorkspaceSeenAt"):
        workspace_snapshots = perception.get("workspaceArtifactSnapshots", {})
        if not isinstance(workspace_snapshots, dict):
            workspace_snapshots = {}
        workspace_signal = {
            "type": "workspace-changed",
            "latestMtime": latest_workspace.get("latestMtime"),
            "path": latest_workspace.get("path"),
            "provenance": latest_workspace.get("provenance"),
            "salience": salience_map.get(
                "workspace-user-changed" if latest_workspace.get("provenance") == "user-change" else "workspace-changed",
                "medium" if latest_workspace.get("provenance") == "user-change" else "low",
            ),
        }
        counters = perception.setdefault("signalCounters", {})
        counters["workspaceChanged"] = counters.get("workspaceChanged", 0) + 1
        perception["lastWorkspaceSeenAt"] = latest_workspace.get("latestMtime")
        perception["lastWorkspaceSeenPath"] = latest_workspace.get("path")
        perception["lastWorkspaceProvenance"] = latest_workspace.get("provenance")

        rel = latest_workspace.get("path")
        if rel:
            target = ROOT / Path(rel)
            snapshot = workspace_artifact_snapshot(target)
            previous_snapshot = workspace_snapshots.get(rel, {}) if isinstance(workspace_snapshots.get(rel), dict) else {}
            if snapshot:
                old_hash = previous_snapshot.get("contentHash")
                new_hash = snapshot.get("contentHash")
                workspace_signal.update({
                    "artifactKind": snapshot.get("kind"),
                    "artifactTextReadable": snapshot.get("textReadable"),
                    "artifactSizeBytes": snapshot.get("sizeBytes"),
                    "oldContentHash": old_hash,
                    "newContentHash": new_hash,
                    "artifactDiffAvailable": bool(old_hash and new_hash and old_hash != new_hash),
                })
                workspace_snapshots[rel] = {
                    "contentHash": new_hash,
                    "sizeBytes": snapshot.get("sizeBytes"),
                    "suffix": snapshot.get("suffix"),
                    "textReadable": snapshot.get("textReadable"),
                    "kind": snapshot.get("kind"),
                    "latestMtime": latest_workspace.get("latestMtime"),
                }
                workspace_snapshots = trim_snapshot_map(workspace_snapshots, int(config.get("maxWorkspaceArtifactSnapshots", 40)))
                perception["workspaceArtifactSnapshots"] = workspace_snapshots

        if latest_workspace.get("provenance") == "self-write" and not config.get("emitSelfWriteWorkspaceSignals", False):
            suppressed_signals.append(workspace_signal)
            counters["workspaceSelfWriteSuppressed"] = counters.get("workspaceSelfWriteSuppressed", 0) + 1
        else:
            signals.append(workspace_signal)
            if latest_workspace.get("provenance") == "user-change":
                counters["workspaceUserChanged"] = counters.get("workspaceUserChanged", 0) + 1

    existing = perception.setdefault("recentSignals", [])
    for signal in signals:
        append_signal(existing, signal, compress=compress_history)
    trim_history(existing, int(config.get("maxRecentSignals", 30)))

    suppressed_history = perception.setdefault("recentSuppressedSignals", [])
    for signal in suppressed_signals:
        append_signal(suppressed_history, signal, compress=compress_history)
    trim_history(suppressed_history, int(config.get("maxRecentSuppressedSignals", 12)))

    perception["lastProbeSignals"] = signals
    perception["lastSuppressedSignals"] = suppressed_signals
    perception["lastSignalProbeAt"] = now_iso()
    perception["updatedAt"] = perception["lastSignalProbeAt"]

    save_json(perception_path, perception)
    emit_json({
        "ok": True,
        "signals": signals,
        "suppressedSignals": suppressed_signals,
        "signalCount": len(signals),
        "suppressedSignalCount": len(suppressed_signals),
        "updatedAt": perception["updatedAt"],
    })


if __name__ == "__main__":
    main()
