from __future__ import annotations

import os, shutil, time, json

BF = r"C:\Users\15305\.openclaw\workspace\brainflow"
ts = time.strftime("%Y%m%d-%H%M%S")
bak = os.path.join(BF, f"_reset_backup_{ts}")
os.makedirs(bak, exist_ok=True)

def move(src_rel: str):
    src = os.path.join(BF, src_rel)
    if os.path.exists(src):
        dst = os.path.join(bak, src_rel.replace("\\", "_").replace("/", "_"))
        shutil.move(src, dst)

# move logs/state
for rel in [
    "runs",
    os.path.join("outbox", "candidates.jsonl"),
    os.path.join("outbox", "cursor.txt"),
    os.path.join("outbox", "dedup_index.json"),
    os.path.join("memory", "episodic"),
    "state_acc.json",
    "state_task_queue.json",
    "state_cycle.json",
]:
    move(rel)

# recreate minimal structure
os.makedirs(os.path.join(BF, "runs"), exist_ok=True)
os.makedirs(os.path.join(BF, "memory", "episodic"), exist_ok=True)
os.makedirs(os.path.join(BF, "outbox"), exist_ok=True)

open(os.path.join(BF, "outbox", "candidates.jsonl"), "w", encoding="utf-8").write("")
open(os.path.join(BF, "outbox", "cursor.txt"), "w", encoding="utf-8").write("0\n")
open(os.path.join(BF, "outbox", "dedup_index.json"), "w", encoding="utf-8").write(json.dumps({"maxPerKind": 500, "seen": {}}, ensure_ascii=False, indent=2))
open(os.path.join(BF, "state_acc.json"), "w", encoding="utf-8").write(json.dumps({"lastHash": "", "repeatCount": 0, "lastTs": 0}, ensure_ascii=False, indent=2))
open(os.path.join(BF, "state_task_queue.json"), "w", encoding="utf-8").write(json.dumps({"pending": [], "done": [], "max_done": 500}, ensure_ascii=False, indent=2))
open(os.path.join(BF, "state_cycle.json"), "w", encoding="utf-8").write(json.dumps({"stage": 0, "stages": ["evidence_table", "deep_dive", "skill_build", "reflect"], "lastStageTs": 0, "notes": "reset"}, ensure_ascii=False, indent=2))

print(bak)
