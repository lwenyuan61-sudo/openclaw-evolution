# Wake Model

目标：让the agent的持续性依赖统一状态层与事件恢复，而不是依赖 cron 定时推动。

## Default wake drivers

当前默认唤醒来源：

1. `direct-user`：Lee 的直接消息或明确命令
2. `heartbeat`：宿主提供的周期性恢复点
3. `local-signal`：本地屏幕、设备、文件、音视频等真实信号
4. `manual-maintenance`：明确需要时的人为触发检查

## Non-goal

- 不把 cron 作为持续性的必要条件
- 不为了“看起来持续活着”而维持额外的定时自转
- 不把调度频率本身当成价值

## Rule

- 持续性来自 `self-state -> attention -> homeostasis -> continuity -> write-back`
- resident loop 可以作为常驻底座，但它服务于状态连续性与现实信号接入，不等于持续高成本推理
- 没有高价值事件时，允许安静存在，而不是靠额外调度制造动作
- 如果 heartbeat 已足够提供恢复点，就不要额外创建 cron
- 如果未来需要精确提醒或单次定时任务，可以把 cron 当外部提醒器，而不是主意识循环
