# Adaptive Cron

目标：让 cron 不再只是固定频率触发器，而是成为the agent根据近期价值、安静窗口、对话活跃度与阻塞情况主动调整的节奏层。

## Current direction from Lee

Lee 明确要求：
- 每次任务后，根据新的想法与指标考虑是否调整 cron
- 成长目标不是“固定脚本一直跑”，而是逐步接近有学习能力、能持续适应环境的本地智能体
- 需要解决“工作期间用户新消息与任务完成后的信息流衔接不自然”的问题

## First practical rule

后续每次 cron 自检结束前，至少快速回答：
1. 当前频率是否仍有边际价值？
2. 当前是否处于 low-activity window？若是，是否应降频？
3. 最近是否有用户主动对话增加？若有，是否应转向更短暂的观察窗口而不是固定自检？
4. 是否存在“任务执行期间新消息未被自然衔接”的现象，需要在调度层专门补机制？

## Immediate implication

当前已经进入 low-activity window，5 分钟自检频率的边际价值正在下降。
因此，下一次适合的自治调整应优先评估：
- 是否把 5 分钟改为 15 分钟或 30 分钟
- 是否为“用户最近有直接互动”保留更灵活的短期观察逻辑，而不是永久高频

## Messaging continuity problem

需要单列为后续问题：
- 当the agent在执行中，Lee 的新消息是否会打断 / 排队 / 形成新的 run
- 任务结束后的回复为什么没有自然并入 Lee 视角下的当前对话
- 后续应查 OpenClaw 的 session / cron / delivery 行为，设计一个更自然的衔接策略

## Practical cadence ladder

把每轮结束时的 cadence 判断固定成以下顺序，减少夜间反复犹豫：

1. 先看时间窗：23:00-08:00 默认视为 low-activity window
2. 再看最近价值：
   - 连续 2 轮高价值且仍在建设同一 focus：可保留 5m
   - 连续 3 轮低价值：降到 15m
   - 连续 5 轮低价值：降到 30m
3. 若当前 wake 虽有 artifact，但主要是内部治理/记录，且仍处于 low-activity window：默认不要因为“终于做出点东西”就立刻回到 5m
4. 只有出现下面任一项，才在 low-activity window 中重新提高频率：
   - Lee 的新明确指令
   - 用户面向的高价值机会
   - 明确 blocker 需要快速跟进
   - 同一建设轨道连续多轮稳定产出

## Current implication

在清晨 08:00 前，即使还能做出轻量 artifact，也应优先把 cadence 维持在较慢档位（通常 15m），除非出现明确的用户价值拉动。
这能避免因为少量内部进展就重新回到表演式高频。 
