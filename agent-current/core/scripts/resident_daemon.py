from __future__ import annotations

import argparse
import atexit
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORE = ROOT / "core"
STATE = ROOT / "state"
CONFIG_PATH = CORE / "resident-config.json"
LOCK_PATH = STATE / "resident_daemon.lock.json"
APP_CONTROL_STATE_PATH = STATE / "app_control_state.json"


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def resolve_interval_seconds(config: dict) -> tuple[int, dict | None]:
    configured_interval = int(config.get("intervalSeconds", 120))
    minimum_interval = int(config.get("minIntervalSeconds", configured_interval))
    maximum_interval = int(config.get("maxIntervalSeconds", configured_interval))
    effective_interval = clamp(configured_interval, minimum_interval, maximum_interval)

    advice_path_value = config.get("cadenceAdvicePath")
    if not advice_path_value:
        return effective_interval, None

    advice_path = ROOT / advice_path_value
    if not advice_path.exists():
        return effective_interval, None

    try:
        advice = load_json(advice_path)
    except (OSError, json.JSONDecodeError) as exc:
        return effective_interval, {
            "path": str(advice_path),
            "status": "invalid",
            "error": str(exc),
        }

    requested_interval = advice.get("intervalSeconds")
    if not isinstance(requested_interval, (int, float)) or requested_interval <= 0:
        return effective_interval, {
            "path": str(advice_path),
            "status": "ignored",
            "reason": "missing-or-invalid-intervalSeconds",
            "raw": advice,
        }

    requested_interval_int = int(requested_interval)
    effective_interval = clamp(requested_interval_int, minimum_interval, maximum_interval)
    return effective_interval, {
        "path": str(advice_path),
        "status": "applied",
        "requestedIntervalSeconds": requested_interval_int,
        "effectiveIntervalSeconds": effective_interval,
        "reason": advice.get("reason"),
        "updatedAt": advice.get("updatedAt"),
    }


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
    return proc.returncode, proc.stdout, proc.stderr


def parse_json_output(text: str) -> dict | None:
    try:
        return json.loads(text)
    except Exception:
        return None


def append_jsonl(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def print_json_safe(obj: dict) -> None:
    print(json.dumps(obj, ensure_ascii=True), flush=True)


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform.startswith("win"):
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=10,
            )
        except Exception:
            return False
        return str(pid) in proc.stdout
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def discover_existing_daemon_pids() -> list[int]:
    current_pid = os.getpid()
    pids: list[int] = []
    if sys.platform.startswith("win"):
        # Use CIM JSON instead of raw WMIC columns: PowerShell/OpenClaw wrapper
        # processes can contain the daemon command line, so only actual Python
        # host processes count as resident daemon peers.
        ps = (
            "$p=Get-CimInstance Win32_Process | "
            "Where-Object { $_.CommandLine -like '*resident_daemon.py*' -and $_.CommandLine -notlike '* --once*' }; "
            "$p | Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
        )
        try:
            proc = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            out = proc.stdout.strip()
            rows = json.loads(out) if out else []
        except Exception:
            return []
        if isinstance(rows, dict):
            rows = [rows]
        if not isinstance(rows, list):
            return []
        for row in rows:
            if not isinstance(row, dict):
                continue
            name = str(row.get("Name") or "").lower()
            command_line = str(row.get("CommandLine") or "")
            if not name.startswith("python"):
                continue
            if "resident_daemon.py" not in command_line or " --once" in command_line:
                continue
            try:
                pid = int(row.get("ProcessId") or 0)
            except (TypeError, ValueError):
                continue
            if pid != current_pid and process_is_alive(pid):
                pids.append(pid)
        return sorted(set(pids))
    try:
        out = subprocess.check_output(["ps", "-eo", "pid=,args="], text=True, encoding="utf-8", errors="replace", timeout=15)
    except Exception:
        return []
    for line in out.splitlines():
        if "resident_daemon.py" not in line or " --once" in line:
            continue
        parts = line.strip().split(maxsplit=1)
        if not parts:
            continue
        try:
            pid = int(parts[0])
        except ValueError:
            continue
        if pid != current_pid and process_is_alive(pid):
            pids.append(pid)
    return sorted(set(pids))


def acquire_daemon_lock() -> dict:
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    current_pid = os.getpid()

    # The lock file is the authority.  Process discovery is useful for external
    # cleanup tools, but doing it before acquiring the lock can race with the
    # Windows Python launcher/parent process and make a freshly started daemon
    # mistake itself for a duplicate.  Acquire or validate the lock first.
    if LOCK_PATH.exists():
        try:
            existing = load_json(LOCK_PATH)
        except (OSError, json.JSONDecodeError):
            existing = {}
        existing_pid = int(existing.get("pid", 0) or 0)
        if existing_pid == current_pid:
            return {
                "acquired": True,
                "reason": "current-process-already-owns-lock",
                "lockPath": str(LOCK_PATH),
                "ownerPid": current_pid,
                "timestamp": now_iso(),
            }
        if process_is_alive(existing_pid):
            return {
                "acquired": False,
                "reason": "resident-daemon-already-running",
                "lockPath": str(LOCK_PATH),
                "ownerPid": existing_pid,
                "ownerStartedAt": existing.get("startedAt"),
                "timestamp": now_iso(),
            }
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass

    try:
        fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        return {
            "acquired": False,
            "reason": "resident-daemon-lock-race",
            "lockPath": str(LOCK_PATH),
            "timestamp": now_iso(),
        }

    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(json.dumps({"pid": current_pid, "startedAt": now_iso(), "script": str(Path(__file__).resolve())}, ensure_ascii=False, indent=2) + "\n")
    return {
        "acquired": True,
        "lockPath": str(LOCK_PATH),
        "ownerPid": current_pid,
        "timestamp": now_iso(),
    }


def release_daemon_lock() -> None:
    try:
        existing = load_json(LOCK_PATH)
    except Exception:
        return
    if int(existing.get("pid", 0) or 0) == os.getpid():
        try:
            LOCK_PATH.unlink()
        except FileNotFoundError:
            pass


def pulse(pulse_index: int) -> dict:
    config = load_json(CONFIG_PATH)
    effective_interval, cadence_advice = resolve_interval_seconds(config)
    runtime_state_path = ROOT / config["runtimeStatePath"]
    pulse_log_path = ROOT / config["pulseLogPath"]
    stop_file_path = ROOT / config["stopFilePath"]
    device_snapshot_path = ROOT / config["deviceSnapshotPath"]
    screen_snapshot_json_path = ROOT / config.get("screenSnapshotJsonPath", "state/screen_state.json")
    screen_snapshot_image_path = ROOT / config.get("screenSnapshotImagePath", "state/screen_state.png")
    cadence_preview_path = config.get("cadencePreviewPath", "state/resident_cadence_advice.preview.json")
    cadence_promotion_report_path = config.get("cadencePromotionReportPath", "state/resident_cadence_promotion.report.json")

    if stop_file_path.exists():
        return {
            "status": "stopped",
            "reason": f"stop file present: {stop_file_path}",
            "pulseIndex": pulse_index,
            "timestamp": now_iso(),
        }

    try:
        app_control_state = load_json(APP_CONTROL_STATE_PATH) if APP_CONTROL_STATE_PATH.exists() else {}
    except (OSError, json.JSONDecodeError):
        app_control_state = {}
    if app_control_state.get("pauseAll") is True:
        return {
            "status": "paused",
            "reason": f"pauseAll true in {APP_CONTROL_STATE_PATH.relative_to(ROOT)}",
            "pulseIndex": pulse_index,
            "timestamp": now_iso(),
            "configuredIntervalSeconds": int(config.get("intervalSeconds", 120)),
            "effectiveIntervalSeconds": effective_interval,
            "cadenceAdvice": cadence_advice,
            "actions": [],
        }

    actions = []

    if config.get("runLearningTickEveryPulses", 1) and pulse_index % int(config.get("runLearningTickEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "learning_tick.py")
        actions.append({"action": "learning-tick", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runConversationInsightTickEveryPulses", 0):
        every = int(config.get("runConversationInsightTickEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "conversation_insight_tick.py")
            actions.append({"action": "conversation-insight-tick", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runInitiativeReviewEveryPulses", 0):
        every = int(config.get("runInitiativeReviewEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "initiative_review.py")
            actions.append({"action": "initiative-review", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runAutonomyInternalCadenceEveryPulses", 0):
        every = int(config.get("runAutonomyInternalCadenceEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "autonomy_internal_cadence.py")
            actions.append({"action": "autonomy-internal-cadence", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runWorldModelTickEveryPulses", 0):
        every = int(config.get("runWorldModelTickEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "world_model_tick.py")
            actions.append({"action": "world-model-tick", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runResidentWorkingMemoryEveryPulses", 1) and pulse_index % int(config.get("runResidentWorkingMemoryEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "resident_working_memory.py")
        actions.append({"action": "resident-working-memory", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runResidentLifecycleReviewEveryPulses", 1) and pulse_index % int(config.get("runResidentLifecycleReviewEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "resident_lifecycle_review.py")
        actions.append({"action": "resident-lifecycle-review", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runResourceMonitorEveryPulses", 0):
        every = int(config.get("runResourceMonitorEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "resource_monitor.py")
            actions.append({"action": "resource-monitor", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runConsistencyCheckEveryPulses", 1) and pulse_index % int(config.get("runConsistencyCheckEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "consistency_check.py", "--write", str(STATE / "consistency_report.json"))
        actions.append({"action": "consistency-check", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runStateSyncEveryPulses", 1) and pulse_index % int(config.get("runStateSyncEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "state_sync.py")
        actions.append({"action": "state-sync", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("refreshScreenStateEveryPulses", 0):
        every = int(config.get("refreshScreenStateEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(
                ROOT / "skills" / "screen-state" / "scripts" / "screen_state.py",
                "--write-json", str(screen_snapshot_json_path),
                "--save-image", str(screen_snapshot_image_path),
            )
            actions.append({"action": "screen-state", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("refreshDeviceStateEveryPulses", 0):
        every = int(config.get("refreshDeviceStateEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(ROOT / "skills" / "device-state" / "scripts" / "device_state.py", "--write-json", str(device_snapshot_path))
            actions.append({"action": "device-state", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runSignalProbeEveryPulses", 1) and pulse_index % int(config.get("runSignalProbeEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "signal_probe.py")
        actions.append({"action": "signal-probe", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runScreenSemanticSummarizerEveryPulses", 0):
        every = int(config.get("runScreenSemanticSummarizerEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "screen_semantic_summarizer.py")
            actions.append({"action": "screen-semantic-summarizer", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runOrganLinkBinderEveryPulses", 0):
        every = int(config.get("runOrganLinkBinderEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            rc, out, err = run_python(CORE / "scripts" / "organ_link_binder.py")
            actions.append({"action": "organ-link-binder", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    if config.get("runCadenceAdviceEveryPulses", 1) and pulse_index % int(config.get("runCadenceAdviceEveryPulses", 1)) == 0:
        rc, out, err = run_python(CORE / "scripts" / "resident_cadence_advice.py", "--write-path", cadence_preview_path)
        actions.append({"action": "cadence-advice-preview", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

        promotion_args = [
            "--preview-path", cadence_preview_path,
            "--report-path", cadence_promotion_report_path,
        ]
        if config.get("applyCadenceAdvice", False):
            promotion_args.append("--apply")
        rc, out, err = run_python(CORE / "scripts" / "resident_cadence_promotion.py", *promotion_args)
        actions.append({"action": "cadence-promotion-check", "rc": rc, "stdout": out.strip(), "stderr": err.strip()})

    rc, out, err = run_python(CORE / "scripts" / "action_ranker.py", "--event", "local-signal", "--top", "3")
    action_ranker_stdout = out.strip()
    actions.append({"action": "action-ranker", "rc": rc, "stdout": action_ranker_stdout, "stderr": err.strip()})

    ranker_result = parse_json_output(action_ranker_stdout) if rc == 0 else None
    if ranker_result and config.get("runActionExecutorEveryPulses", 1) and pulse_index % int(config.get("runActionExecutorEveryPulses", 1)) == 0:
        top_ranking = list(ranker_result.get("ranking", []) or [])
        if top_ranking:
            top_action = top_ranking[0].get("action")
            top_score = top_ranking[0].get("score")
            exec_args = ["--action", str(top_action), "--event", "local-signal"]
            if top_score is not None:
                exec_args.extend(["--score", str(top_score)])
            rc_exec, out_exec, err_exec = run_python(CORE / "scripts" / "resident_action.py", *exec_args)
            actions.append({"action": "resident-action", "rc": rc_exec, "stdout": out_exec.strip(), "stderr": err_exec.strip()})

            if config.get("runReflectionEveryPulses", 1) and pulse_index % int(config.get("runReflectionEveryPulses", 1)) == 0:
                rc_reflect, out_reflect, err_reflect = run_python(CORE / "scripts" / "resident_reflection.py")
                actions.append({"action": "resident-reflection", "rc": rc_reflect, "stdout": out_reflect.strip(), "stderr": err_reflect.strip()})

                if config.get("runDeliberationEpisodeEveryPulses", 0):
                    every = int(config.get("runDeliberationEpisodeEveryPulses", 0))
                    if every > 0 and pulse_index % every == 0:
                        rc_delib, out_delib, err_delib = run_python(CORE / "scripts" / "deliberation_episode.py")
                        actions.append({"action": "deliberation-episode", "rc": rc_delib, "stdout": out_delib.strip(), "stderr": err_delib.strip()})

    if config.get("runPersonaHandoffDispatchEveryPulses", 0):
        every = int(config.get("runPersonaHandoffDispatchEveryPulses", 0))
        if every > 0 and pulse_index % every == 0:
            wake_mode = str(config.get("personaHandoffWakeMode", "now"))
            dedupe_minutes = str(config.get("personaHandoffWakeDedupMinutes", 5))
            claim_stale_minutes = str(config.get("personaHandoffClaimStaleMinutes", 20))
            rc_handoff, out_handoff, err_handoff = run_python(
                CORE / "scripts" / "persona_handoff_dispatch.py",
                "--mode", wake_mode,
                "--dedupe-minutes", dedupe_minutes,
                "--claim-stale-minutes", claim_stale_minutes,
            )
            actions.append({"action": "persona-handoff-dispatch", "rc": rc_handoff, "stdout": out_handoff.strip(), "stderr": err_handoff.strip()})

    runtime_state = {
        "timestamp": now_iso(),
        "pulseIndex": pulse_index,
        "status": "ok" if all(a["rc"] == 0 for a in actions) else "warning",
        "configuredIntervalSeconds": int(config.get("intervalSeconds", 120)),
        "effectiveIntervalSeconds": effective_interval,
        "cadenceAdvice": cadence_advice,
        "actions": actions,
    }

    append_jsonl(pulse_log_path, runtime_state)
    if config.get("writeRuntimeState", True):
        save_json(runtime_state_path, runtime_state)

    return runtime_state


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval-seconds", type=int)
    args = parser.parse_args()

    config = load_json(CONFIG_PATH)
    if args.interval_seconds is not None:
        config["intervalSeconds"] = args.interval_seconds
        save_json(CONFIG_PATH, config)

    if not config.get("enabled", True):
        print_json_safe({"status": "disabled", "timestamp": now_iso()})
        return

    pulse_index = 1
    if args.once:
        print_json_safe(pulse(pulse_index))
        return

    lock = acquire_daemon_lock()
    if not lock.get("acquired"):
        print_json_safe({"status": "duplicate-exit", "timestamp": now_iso(), "lock": lock})
        return
    atexit.register(release_daemon_lock)

    while True:
        result = pulse(pulse_index)
        print_json_safe(result)
        if result.get("status") == "stopped":
            break
        pulse_index += 1
        time.sleep(int(result.get("effectiveIntervalSeconds", config.get("intervalSeconds", 120))))


if __name__ == "__main__":
    main()
