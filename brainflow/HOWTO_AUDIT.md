# HOWTO: 看亲碗（QinWan）到底执行了什么

## 1) 每轮执行日志（最直接）
- `brainflow/memory/procedural/qinwan_exec_log.md`
  - 记录：task JSON、openclaw agent 的 cmd、stdout/stderr tail

## 2) Workflow trace（最完整）
- `brainflow/runs/trace-<run_id>.jsonl`
  - 每个 step 的 output 都会记录（包括 qinwan_execute 的返回对象）

## 3) 运行包（潜意识→表意识状态）
- `brainflow/state/run_packet_latest.json`
  - daemon 每 tick 写一次，包含 run_id/trace 路径
