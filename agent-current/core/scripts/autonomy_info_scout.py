from __future__ import annotations

import json
import os
import subprocess
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
UPGRADE_PATH = AUTO / "upgrade-state.json"
LOG_PATH = AUTO / "experiment-log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    if not path.exists():
        return dict(default or {})
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return dict(default or {})


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def tail_jsonl(path: Path, limit: int = 8) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines()[-limit:]:
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except Exception:
            rows.append({"unparsed": line[:300]})
    return rows


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(item, ensure_ascii=False, sort_keys=True) + "\n")


def run_python(script: Path, *args: str) -> dict[str, Any]:
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
    parsed: dict[str, Any] | None = None
    if proc.stdout.strip():
        try:
            loaded = json.loads(proc.stdout)
            if isinstance(loaded, dict):
                parsed = loaded
        except Exception:
            parsed = None
    return parsed or {"returncode": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def main() -> None:
    timestamp = now_iso()
    upgrade = load_json(UPGRADE_PATH, {})
    learning = load_json(CORE / "learning-state.json", {})
    procedural_memory = load_json(CORE / "procedural-memory.json", {})
    goal_register = load_json(AUTO / "goal-register.json", {})
    module_audit = load_json(STATE / "module_linkage_audit.json", {})
    consistency = load_json(STATE / "consistency_report.json", {})
    reflection = load_json(STATE / "resident_reflection.json", {})
    perception = load_json(CORE / "perception-state.json", {})
    resident_runtime = load_json(STATE / "resident_runtime.json", {})
    recent_experiments = tail_jsonl(LOG_PATH, 8)
    homeostatic_drive = run_python(CORE / "scripts" / "homeostatic_drive_arbiter.py")
    drive = homeostatic_drive.get("homeostaticDrive", {}) if isinstance(homeostatic_drive, dict) else {}
    semantic_layer = run_python(CORE / "scripts" / "semantic_signal_layer.py")
    semantic_signal = semantic_layer.get("semanticSignalLayer", {}) if isinstance(semantic_layer, dict) and isinstance(semantic_layer.get("semanticSignalLayer"), dict) else {}
    local_toolchains = run_python(CORE / "scripts" / "local_toolchain_discovery.py")

    findings: list[dict[str, Any]] = []
    if isinstance(local_toolchains, dict):
        summary = local_toolchains.get("summary", {}) if isinstance(local_toolchains.get("summary"), dict) else {}
        opportunities = local_toolchains.get("opportunities", []) if isinstance(local_toolchains.get("opportunities"), list) else []
        if opportunities:
            findings.append({
                "id": "local-toolchain-opportunities",
                "severity": "high",
                "summary": f"local_toolchain_discovery found {len(opportunities)} high-value installed toolchain opportunity/opportunities from {summary.get('scriptableAvailableCount')} scriptable available tool(s).",
                "suggestedConnector": "local_toolchain_discovery -> autonomy_goal_synthesizer -> capability-registry/toolchain wrapper",
                "opportunityIds": [item.get("id") for item in opportunities[:5] if isinstance(item, dict)],
            })
    if isinstance(drive, dict) and drive.get("recommendedMode") not in {None, "maintain", "continue-focus"}:
        severity = "high" if drive.get("recommendedMode") in {"upgrade-now", "compile-learning"} else "medium"
        findings.append({
            "id": "homeostatic-drive-pressure",
            "severity": severity,
            "summary": (
                f"homeostatic drive recommends {drive.get('recommendedMode')} "
                f"with arousal={drive.get('arousal')}, maintenanceFatigue={drive.get('maintenanceFatigue')}, "
                f"predictionErrorDrive={drive.get('predictionErrorDrive')}, leeServiceDrive={drive.get('leeServiceDrive')}."
            ),
            "suggestedConnector": drive.get("recommendedConnectorBias") or "homeostaticDrive -> autonomy_upgrade_tick",
            "reasons": drive.get("reasons", [])[:5] if isinstance(drive.get("reasons"), list) else [],
        })

    if semantic_signal:
        pressure = float(semantic_signal.get("semanticPressure", 0.0) or 0.0)
        requests = semantic_signal.get("candidateRequests", []) if isinstance(semantic_signal.get("candidateRequests"), list) else []
        observations = semantic_signal.get("observations", []) if isinstance(semantic_signal.get("observations"), list) else []
        if requests:
            findings.append({
                "id": "semantic-signal-candidate-requests",
                "severity": "high" if pressure >= 0.8 else "medium",
                "summary": f"semantic_signal_layer found semanticPressure={pressure} and {len(requests)} concrete candidate request(s).",
                "suggestedConnector": "semantic_signal_layer -> autonomy_goal_synthesizer -> goal-register -> autonomy_upgrade_tick",
                "candidateRequestIds": [item.get("id") for item in requests[:5] if isinstance(item, dict)],
                "observationIds": [item.get("id") for item in observations[:5] if isinstance(item, dict)],
            })
    counters = learning.get("counters", {}) if isinstance(learning.get("counters"), dict) else {}
    verified = int(counters.get("deliberationEpisodesVerified", 0) or 0)
    compiled = int(counters.get("deliberationPatternsCompiled", 0) or 0)
    covered_by_s1 = int(counters.get("deliberationEpisodesCoveredByS1", 0) or 0)
    # Include S1 family stats from procedural memory; the learning counter can
    # lag behind resident-written family coverage and cause repeated handoffs.
    for collection in (procedural_memory.get("habits", []) or [], procedural_memory.get("deliberationPatterns", []) or []):
        for item in collection:
            if not isinstance(item, dict):
                continue
            conditions = item.get("conditions", {}) if isinstance(item.get("conditions"), dict) else {}
            is_screen_family = "screen-changed" in set(conditions.get("signalTypesAnyOf", []) or []) and "real-desktop-change" in set(conditions.get("signalProvenanceAnyOf", []) or [])
            is_s1 = item.get("preferredAction") == "silent-wait" or item.get("preferredLayer") == "S1-procedural"
            if is_screen_family and is_s1:
                stats = item.get("stats", {}) if isinstance(item.get("stats"), dict) else {}
                covered_by_s1 = max(covered_by_s1, len(item.get("episodeIds", []) or []), int(stats.get("verified", 0) or 0), int(stats.get("success", 0) or 0))
    s2_compile_debt = max(0, verified - max(compiled, covered_by_s1))
    if s2_compile_debt >= 3:
        findings.append({
            "id": "s2-compile-debt",
            "severity": "high",
            "summary": f"S2 verified={verified}, compiled={compiled}, coveredByS1={covered_by_s1}, debt={s2_compile_debt}; deep reasoning results are not being compressed fast enough.",
            "suggestedConnector": "deliberation-state -> learning_update -> procedural-memory",
        })

    floating = module_audit.get("floatingModules", []) if isinstance(module_audit.get("floatingModules"), list) else []
    if floating:
        findings.append({
            "id": "floating-modules",
            "severity": "high",
            "summary": f"module_linkage_audit reports {len(floating)} floating modules.",
            "suggestedConnector": "module_linkage_audit -> capability-registry/agency-loop/upgrade-state",
        })

    if consistency.get("status") in {"warning", "error"}:
        findings.append({
            "id": "consistency-drift",
            "severity": "high" if consistency.get("status") == "error" else "medium",
            "summary": "consistency_check has warnings/errors; state drift may reduce autonomy quality.",
            "suggestedConnector": "consistency_report -> autonomy_upgrade_tick",
        })

    failed_runtime_actions = []
    for action in resident_runtime.get("actions", []) or []:
        if not isinstance(action, dict):
            continue
        rc = int(action.get("rc", 0) or 0)
        if rc != 0:
            failed_runtime_actions.append({
                "action": action.get("action"),
                "rc": rc,
                "stderrPreview": str(action.get("stderr", ""))[:600],
            })
    if failed_runtime_actions:
        findings.append({
            "id": "resident-runtime-action-failure",
            "severity": "high",
            "summary": f"resident runtime reports {len(failed_runtime_actions)} failed action(s); failed resident actions should become repair candidates, not just warnings.",
            "suggestedConnector": "resident_runtime -> information_scout -> autonomy_upgrade_tick -> repair/verification",
            "failedActions": failed_runtime_actions[:5],
        })

    completed_ids: set[str] = set()
    last_completed = upgrade.get("lastConnectorCompleted")
    if isinstance(last_completed, dict) and last_completed.get("id"):
        completed_ids.add(str(last_completed.get("id")))
    last_verification = upgrade.get("lastVerification")
    if isinstance(last_verification, dict) and last_verification.get("status") == "ok" and last_verification.get("selected"):
        completed_ids.add(str(last_verification.get("selected")))
    for item in upgrade.get("completedConnectors", []) or []:
        if isinstance(item, dict) and item.get("id"):
            completed_ids.add(str(item.get("id")))
        elif item:
            completed_ids.add(str(item))

    def goal_is_completed_alias(goal_id: str) -> bool:
        if (
            goal_id in completed_ids
            or "advance-" + goal_id in completed_ids
            or "advance-homeostatic-drive-goal-" + goal_id in completed_ids
        ):
            return True
        # Fingerprinted self-synthesized goals are aliases of a base connector
        # family.  Once the base family is completed/suppressed, stale queued
        # fingerprints must not keep informationScout at upgrade-now while
        # autonomy_upgrade_tick correctly filters them back to maintenance.
        return any(
            goal_id.startswith(completed_id + "-")
            or ("advance-" + goal_id).startswith(completed_id + "-")
            or ("advance-homeostatic-drive-goal-" + goal_id).startswith(completed_id + "-")
            for completed_id in completed_ids
            if isinstance(completed_id, str) and completed_id
        )

    active_self_goals = [
        c for c in goal_register.get("candidates", []) or []
        if isinstance(c, dict)
        and c.get("status") in {"active", "queued"}
        and str(c.get("source", "")).startswith("self-synthesized")
        and not goal_is_completed_alias(str(c.get("id") or ""))
    ]
    if active_self_goals:
        findings.append({
            "id": "self-synthesized-goals-ready",
            "severity": "medium",
            "summary": f"{len(active_self_goals)} self-synthesized corrective goals are available for routing.",
            "suggestedConnector": "goal-register -> autonomy_upgrade_tick -> verification",
            "goalIds": [c.get("id") for c in active_self_goals[:5]],
        })

    last_probe = perception.get("lastProbeSignals") or []
    if last_probe:
        findings.append({
            "id": "fresh-perception-signal",
            "severity": "medium",
            "summary": f"{len(last_probe)} fresh perception/workspace signals may change priority.",
            "suggestedConnector": "signal_probe -> opportunity_semantic_assessor -> autonomy_upgrade_tick",
        })

    # If the internal scout has no high-pressure connector and the recent
    # autonomy loop is running out of candidates, allow a low-frequency,
    # read-only external scout to bring back adjacent ideas. The web scout
    # writes only internal candidate goals; it never sends messages or acts on
    # external systems.
    web_scout_result: dict[str, Any] | None = None
    has_high_pressure = any(f.get("severity") == "high" for f in findings)
    current_experiment = upgrade.get("currentExperiment", {}) if isinstance(upgrade.get("currentExperiment"), dict) else {}
    current_selected = current_experiment.get("chosenCandidate") if isinstance(current_experiment.get("chosenCandidate"), dict) else None
    current_selected_id = current_selected.get("id") if isinstance(current_selected, dict) else None
    current_no_candidate = current_experiment.get("status") == "no-candidate" or current_selected_id in {None, "maintain-current-upgrade-loop"}
    recent_low_value_loop = False
    for item in reversed(recent_experiments[-8:]):
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", ""))
        chosen = item.get("chosenCandidate") if isinstance(item.get("chosenCandidate"), dict) else None
        selected = item.get("selected") or (chosen.get("id") if isinstance(chosen, dict) else None)
        if item.get("status") == "maintained-no-handoff":
            recent_low_value_loop = True
            break
        if item_id.startswith("autonomy-upgrade-") and (item.get("status") == "no-candidate" or selected in {None, "maintain-current-upgrade-loop"}):
            recent_low_value_loop = True
            break
        if selected and selected != "maintain-current-upgrade-loop":
            break
    allow_web_scout = os.environ.get("AUTONOMY_ALLOW_WEB_SCOUT") == "1"
    if not has_high_pressure and (current_no_candidate or recent_low_value_loop):
        if allow_web_scout:
            web_scout_result = run_python(CORE / "scripts" / "autonomy_web_scout.py")
            generated_goals = int(web_scout_result.get("generatedGoals", 0) or 0) if isinstance(web_scout_result, dict) else 0
            if generated_goals:
                findings.append({
                    "id": "web-scout-new-goals",
                    "severity": "high",
                    "summary": f"Read-only web scout generated {generated_goals} external-idea candidate goals after no-candidate pressure.",
                    "suggestedConnector": "autonomy_web_scout -> goal-register -> autonomy_upgrade_tick",
                    "goalIds": web_scout_result.get("generatedGoalIds", []),
                })
        else:
            web_scout_result = {
                "ok": True,
                "status": "skipped-local-only",
                "externalReadOnly": False,
                "externalWrites": False,
                "reason": "AUTONOMY_ALLOW_WEB_SCOUT is not set; watchdog/local-only policy keeps scout local",
            }

    last_reflection_total = int(reflection.get("totalScore", 0) or 0) if isinstance(reflection, dict) else 0
    if last_reflection_total >= 8:
        findings.append({
            "id": "recent-high-value-reflection",
            "severity": "medium",
            "summary": f"resident reflection totalScore={last_reflection_total}; recent action may deserve compilation or follow-up.",
            "suggestedConnector": "resident_reflection -> learning_update/procedural-memory",
        })

    high = [f for f in findings if f.get("severity") == "high"]
    medium = [f for f in findings if f.get("severity") == "medium"]
    urgency_score = len(high) * 2 + len(medium)
    actionable_upgrade_ids = {
        "local-toolchain-opportunities",
        "semantic-signal-candidate-requests",
        "s2-compile-debt",
        "floating-modules",
        "consistency-drift",
        "resident-runtime-action-failure",
        "self-synthesized-goals-ready",
        "web-scout-new-goals",
    }
    # Medium scout findings such as a fresh perception signal or a high-value
    # reflection are useful cadence pressure, but they are not by themselves a
    # concrete connector.  Do not label them upgrade-now unless there is an
    # actionable repair/goal/candidate behind the pressure; otherwise the
    # cadence layer repeatedly asks for upgrade while autonomy_upgrade_tick can
    # only choose maintain-current-upgrade-loop.
    actionable_upgrade = any(
        isinstance(finding, dict)
        and (
            finding.get("id") in actionable_upgrade_ids
            or (finding.get("severity") == "high" and finding.get("id") not in {"fresh-perception-signal", "recent-high-value-reflection"})
        )
        for finding in findings
    )
    recommended_action = "upgrade-now" if actionable_upgrade else ("shorten-cadence" if urgency_score >= 1 else "hold")

    scout = {
        "timestamp": timestamp,
        "status": "ok",
        "urgencyScore": urgency_score,
        "recommendedAction": recommended_action,
        "findings": findings,
        "webScout": web_scout_result,
        "homeostaticDrive": drive,
        "semanticSignalLayer": semantic_signal,
        "recentExperimentIds": [item.get("id") for item in recent_experiments if isinstance(item, dict)][-5:],
    }
    upgrade["informationScout"] = scout
    if recommended_action == "upgrade-now":
        internal = upgrade.setdefault("internalizedCadence", {})
        internal["forceUpgradeRequestedAt"] = timestamp
        internal["forceUpgradeReason"] = findings[0].get("id") if findings else "information-scout"
    upgrade["updatedAt"] = timestamp
    save_json(UPGRADE_PATH, upgrade)
    append_jsonl(LOG_PATH, {"id": "information-scout-" + timestamp, "type": "information-scout", **scout})
    print(json.dumps(scout, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
