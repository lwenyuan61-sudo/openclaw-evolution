# BrainFlow (NaoChao) × QinWan（亲碗）L3 一体化集成（当前）

## 目标（L3）
- **同一身份**：BrainFlow 每次 LLM 调用都使用“亲碗”的身份/目标/价值体系（GOAL + VALUE_SYSTEM）。
- **一体两态**：
  - BrainFlow OFF → 亲碗是正常对话助手。
  - BrainFlow ON  → 亲碗进入持续自主工作态（潜意识循环 + 表意识输出端口）。
- **强制耦合**：
  - BrainFlow 每轮写 `state/run_packet_latest.json`（潜意识运行包）。
  - QinWan（表意识）每次对外说话前必须读取该运行包，并结合向量库检索。
- **共享向量记忆（本地）**：写入/检索均走 `memory/vector_store/brainflow.sqlite`，embedding 使用本机 Ollama（默认 `nomic-embed-text`）。

## 当前实现要点
- BrainFlow daemon：每 tick 运行工作流后，落盘 run packet，并把摘要 upsert 到向量库。
- QinWan proactive loop（qinwan_mode.py）：
  - 消费 outbox candidates
  - 将候选与外发消息写入向量库
  - 主动触达配额：60 条/小时
  - 夜间（01:00–10:00）提高阈值

## 说明
- 仍保持“工具出口统一”：对外发送消息/调用 OpenClaw 工具由 QinWan 执行，以便审计与统一风控。
- 不可逆动作（删除/覆盖重要文件）仍需要主人确认（见 GOAL.md）。

