"""BrainFlow Daemon (MVP)

- 开机后持续 tick（默认每 10 分钟一次）
- 每次 tick 读取 GOAL.md（人类终极目标）
- 跑一个“空闲思考”工作流 idle_think.yaml

安全说明：
- 当前版本不执行系统命令、不访问外网；只会在 workspace 写日志（runs/）。
"""

from __future__ import annotations

import argparse
import os
import time
import json

from core.engine import WorkflowEngine
from core.vector_store import LocalVectorStore


def _acquire_single_instance_lock(base_dir: str) -> None:
    """Prevent multiple daemon.py instances.

    Windows: use a non-blocking msvcrt file lock and keep the handle open.
    """
    lock_path = os.path.join(base_dir, ".daemon.single.lock")

    # Best-effort: if anything goes wrong, do not crash.
    try:
        f = open(lock_path, "a+", encoding="utf-8")
    except Exception:
        return

    try:
        if os.name == "nt":
            import msvcrt  # type: ignore

            # Lock from start of file; msvcrt.locking locks from current position.
            try:
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1024)
            except OSError:
                print("Another BrainFlow daemon instance is already running (file lock busy). Exiting.")
                raise SystemExit(0)

        # Write PID for debugging; keep file open for lock lifetime.
        try:
            f.seek(0)
            f.truncate(0)
            f.write(str(os.getpid()))
            f.flush()
        except Exception:
            pass

        globals()["_BF_LOCK_FILE"] = f
    except SystemExit:
        try:
            f.close()
        except Exception:
            pass
        raise
    except Exception:
        try:
            f.close()
        except Exception:
            pass
        return


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=int, default=600, help="seconds between ticks (default 600)")
    ap.add_argument("--workflow", default="auto", help="auto | workflows/idle_think_local.yaml | workflows/idle_think_push.yaml | workflows/idle_think_background.yaml")
    ap.add_argument("--push-min-interval", type=int, default=3600, help="minimum seconds between WhatsApp pushes (default 3600)")
    args = ap.parse_args()

    base_dir = os.path.abspath(os.path.dirname(__file__))
    _acquire_single_instance_lock(base_dir)

    engine = WorkflowEngine(base_dir=base_dir)

    # Shared local vector store (L3): BrainFlow always writes run summaries into it.
    vs = LocalVectorStore(
        db_path=os.path.join(base_dir, "memory", "vector_store", "brainflow.sqlite"),
        ollama_base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        embed_model=os.environ.get("BRAINFLOW_EMBED_MODEL", "nomic-embed-text"),
    )

    state_path = os.path.join(base_dir, "state.json")

    def load_state():
        try:
            if os.path.exists(state_path):
                import json
                with open(state_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {"lastPushTs": 0}

    def save_state(st):
        import json
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)

    print(f"BrainFlow daemon started. interval={args.interval}s workflow={args.workflow} pushMinInterval={args.push_min_interval}s")
    print("Mode note: interval=0 means continuous loop (we still yield briefly to avoid CPU spin).")
    while True:
        try:
            # 每次 tick 都把 goal 文件内容注入环境变量，便于工作流引用
            goal_path = os.path.join(base_dir, "GOAL.md")
            goal_text = ""
            if os.path.exists(goal_path):
                with open(goal_path, "r", encoding="utf-8") as f:
                    goal_text = f.read()
            os.environ["BRAINFLOW_GOAL"] = goal_text

            # Load control (topic/pause + L3 knobs) set by 表意识/亲碗
            ctrl_path = os.path.join(base_dir, "state_control.json")
            ctrl = {}
            paused = False
            paused_until_ts = 0
            topic = "longevity"
            try:
                if os.path.exists(ctrl_path):
                    ctrl = json.load(open(ctrl_path, "r", encoding="utf-8"))
                    paused = bool(ctrl.get("paused", False))
                    paused_until_ts = int(ctrl.get("paused_until_ts", 0) or 0)
                    topic = str(ctrl.get("topic", topic) or topic)
            except Exception:
                ctrl = {}

            # Load QinWan intent (drive/query) to steer 潜意识
            intent_path = os.path.join(base_dir, "state_qinwan_intent.json")
            intent = {}
            drive = 0.8
            query = ""
            try:
                if os.path.exists(intent_path):
                    intent = json.load(open(intent_path, "r", encoding="utf-8"))
                    drive = float(intent.get("drive", drive))
                    query = str(intent.get("query", "") or "")
                    # allow intent to override topic if provided
                    ft = intent.get("focus_topics")
                    if isinstance(ft, list) and ft:
                        topic = str(ft[0] or topic)
            except Exception:
                intent = {}

            # clamp drive
            if drive < 0: drive = 0
            if drive > 1: drive = 1

            # ensure query exists
            if not query.strip():
                query = f"2026 {topic} trial randomized rapamycin senolytic partial reprogramming epigenetic clock review"

            os.environ["BRAINFLOW_TOPIC"] = topic
            os.environ["BRAINFLOW_DRIVE"] = str(drive)
            os.environ["BRAINFLOW_QUERY"] = query

            # DeepThinking uses OpenClaw tools (GPT) for thinking/search; disable Exa plugin path.
            os.environ["BRAINFLOW_DISABLE_SEARCH"] = "1"
            os.environ["BRAINFLOW_USE_GPT"] = "1"
            # Prefer LLM-based judges/decomposition (value/bg/feasibility/htn) over heuristics.
            os.environ["BRAINFLOW_LLM_JUDGES"] = os.environ.get("BRAINFLOW_LLM_JUDGES", "1")

            # Subconscious rule: only allow proactive surfacing when explicitly enabled by control.
            # (Owner conversation is always priority #1.)
            proactive_enabled = bool(ctrl.get("proactive_enabled", False)) if isinstance(ctrl, dict) else False
            proactive_mode = str(ctrl.get("proactive_mode", "medium") or "medium").strip().lower() if isinstance(ctrl, dict) else "medium"
            os.environ["BRAINFLOW_PROACTIVE_ENABLED"] = "1" if proactive_enabled else "0"
            os.environ["BRAINFLOW_PROACTIVE_MODE"] = proactive_mode

            # choose workflow
            wf_path = args.workflow
            if wf_path == "auto":
                # Offline loop by default; online search is delegated to OpenClaw/对话区.
                wf_path = "workflows/idle_think_offline.yaml"

            now_ts = int(time.time())
            if paused and paused_until_ts and now_ts >= paused_until_ts:
                # auto-unpause
                try:
                    import json
                    ctrl = json.load(open(ctrl_path, "r", encoding="utf-8")) if os.path.exists(ctrl_path) else {}
                    ctrl["paused"] = False
                    ctrl["paused_until_ts"] = 0
                    with open(ctrl_path, "w", encoding="utf-8") as f:
                        json.dump(ctrl, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                paused = False

            run_result = None
            run_ok = False
            if not paused:
                run_result = engine.run_from_file(wf_path)
                run_ok = bool(run_result.get("ok")) if isinstance(run_result, dict) else False
            else:
                print("[daemon] paused by state_control.json")

            # L3: write run packet every tick (even if paused/error, best-effort)
            try:
                state_dir = os.path.join(base_dir, "state")
                os.makedirs(state_dir, exist_ok=True)
                rp_path = os.path.join(state_dir, "run_packet_latest.json")
                now = int(time.time())
                rp = {
                    "t": now,
                    "ok": run_ok,
                    "paused": paused,
                    "workflow": wf_path,
                    "topic": topic,
                    "drive": drive,
                    "query": query,
                    "ctrl": ctrl,
                    "intent": intent,
                    "engine": {
                        "run_id": (run_result or {}).get("run_id") if isinstance(run_result, dict) else None,
                        "trace": (run_result or {}).get("trace") if isinstance(run_result, dict) else None,
                        "error": (run_result or {}).get("error") if isinstance(run_result, dict) else None,
                    },
                    "vars": (run_result or {}).get("vars") if isinstance(run_result, dict) else None,
                }
                # Atomic write to avoid empty/partial files on crash.
                tmp_path = rp_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(rp, f, ensure_ascii=False, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                try:
                    os.replace(tmp_path, rp_path)
                except Exception:
                    # fallback best-effort
                    with open(rp_path, "w", encoding="utf-8") as f:
                        json.dump(rp, f, ensure_ascii=False, indent=2)

                # Also upsert a short summary into the local vector store.
                run_id = rp["engine"]["run_id"] or f"ts:{now}"
                summary_lines = [
                    f"topic={topic}",
                    f"workflow={wf_path}",
                    f"ok={run_ok}",
                ]
                if rp["engine"]["error"]:
                    summary_lines.append(f"error={rp['engine']['error']}")
                # Keep summary text compact; full vars remain on disk.
                summary = "BrainFlow run packet: " + ", ".join(summary_lines)
                vs.upsert(
                    doc_id=f"run:{run_id}",
                    text=summary,
                    meta={"topic": topic, "workflow": wf_path, "ok": run_ok, "ts": now},
                    doc_type="run_packet",
                    importance=5.0 if run_ok else 7.0,
                    ts=now,
                )
            except Exception as _e:
                # never crash the daemon for run-packet bookkeeping
                pass
        except KeyboardInterrupt:
            print("\nDaemon stopped.")
            return
        except Exception as e:
            # Level-4 reliability: always persist full traceback so we can root-cause crashes.
            import traceback
            tb = traceback.format_exc()
            print(f"Tick error: {e}")
            print(tb)
            try:
                log_path = os.path.join(base_dir, "logs", "daemon_crash.log")
                os.makedirs(os.path.dirname(log_path), exist_ok=True)
                with open(log_path, "a", encoding="utf-8", errors="replace") as f:
                    f.write("\n" + "="*80 + "\n")
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n")
                    f.write(str(e) + "\n")
                    f.write(tb + "\n")
            except Exception:
                pass

        # Continuous thinking: if interval==0, immediately start next tick after a tiny yield.
        sleep_s = args.interval if args.interval and args.interval > 0 else 2
        time.sleep(sleep_s)


if __name__ == "__main__":
    main()
