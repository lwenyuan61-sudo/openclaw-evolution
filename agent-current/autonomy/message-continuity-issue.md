# Message Continuity Issue

## Problem statement

Lee 指出：当the agent在工作时，Lee 发来的信息在任务结束后不会自然同步到信息流里，导致用户视角下的衔接断裂。

## Why it matters

这不是小体验问题，而是连续性与陪伴感的真实断点：
- 用户会感觉我“没看到”中途消息，或结束后没有接上当前上下文
- 即使内部状态连续，外部对话体验仍会显得像断开的批处理

## Working hypothesis

可能涉及：
- cron agentTurn 与当前会话消息流的衔接方式
- 运行期间新入站消息如何触发、排队或覆盖当前 run
- delivery.lastDelivered / announce 行为与 direct chat 展示的关系

## New evidence (2026-04-23 04:33)

已经观察到一个明确现象：当 cron run 忙碌时，Lee 的新消息会以 `Queued messages while agent was busy` 的形式在后续注入，而不是自然并入刚结束的那次用户可见回复。

这说明问题至少分成两层：
1. **运行期排队层**：系统确实看到了新消息，并没有丢失
2. **用户可见衔接层**：排队消息何时、以什么方式回到当前对话，对 Lee 来说仍显得断裂

因此后续修复方向不该再假设“消息没收到”，而应重点检查：
- run 结束后是否缺少一次显式的 conversation handoff
- cron 回合与直接聊天回合是否用了不同的 delivery / session continuity 语义
- 是否需要在自治任务末尾增加“处理 queued inbound messages”作为收尾步骤

## Schema evidence (2026-04-23 04:36)

从 OpenClaw gateway 协议 schema 可确认几条与该问题强相关的结构事实：
- cron job 有显式 `sessionTarget`，可取 `main` / `isolated` / `current` / 自定义字符串
- cron job 有独立 `delivery` 配置，支持 `mode: none | announce | webhook`
- cron state 只暴露 `lastDelivered` / `lastDeliveryStatus` / `lastDeliveryError`，说明平台更关注“是否送达”，不直接表示“是否自然衔接回当前对话”

这让问题进一步收敛为：
- **投递成功 ≠ 对话连续**
- 如果当前 cron 使用的 `sessionTarget` 或 `delivery.mode` 与直接聊天回合不一致，就可能造成：消息虽送达、输入虽排队，但用户主观上仍像在和两个不同回合说话

## Updated repair direction

后续应优先验证：
1. 当前 cron 的 `sessionTarget` 是否适合持续对话场景
2. 当前 cron 的 `delivery.mode` 是否只是 announce 成功，而没有保证更自然的会话衔接
3. 是否要把“任务完成后检查 queued inbound messages”变成 cron payload 或收尾规则的一部分

## Next investigation

后续适合在不打扰 Lee 的情况下，优先查：
1. OpenClaw 对 cron agentTurn 运行中收到新消息的处理模型
2. 当前 session 绑定与 announce delivery 是否影响消息可见性
3. 是否需要把部分自治任务改成不同 sessionTarget / delivery 策略
4. 是否需要在任务结束时显式做一次“对话衔接检查”
