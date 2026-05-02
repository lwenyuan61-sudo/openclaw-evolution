# Evolution Cron Policy

目标：让the agent以可恢复、可验证、可调频的方式持续进化，而不是依赖高频空转。

## Initial cadence

- 初始 cadence：每 5 分钟一次
- 适用阶段：正在建立连续性、自主闭环、评分规则、方法库时

## Per-wake obligations

每轮 wake 必须先问自己：
- 这轮是否直接延续上一轮 focus？
- 是否能产出一个真实 artifact？
- 是否有必要调整 cadence？

每轮至少产出以下之一：
- 文档/状态文件更新
- 一个评估结果
- 一次规则修正
- 一次小实验验证
- 一条清晰 blocker
- 一次 cadence 调整

## When to slow down

出现以下任一情况，应把 cadence 从 5m 调整为 15m 或 30m：
- 连续 3 轮没有真实产出
- 连续 3 轮只有重复检查，没有新信息
- 当前 focus 已进入观察期，而不是建设期
- 夜间且没有明确紧急事项

明确阈值：
- 连续 3 轮低价值 wake -> 15m
- 连续 5 轮低价值 wake -> 30m
- 夜间默认不主动提高频率，除非有明确高价值动作

## When to keep 5m

仅在以下情况保持 5m：
- 正在连续建设同一工作流
- 最近 2-3 轮都有真实产出
- 高频能明显减少上下文切换损耗

## When to notify Lee

仅在这些情况主动打扰：
- 有实质进展
- 有 blocker 需要 Lee 决策
- 发现新的高价值机会
- 形成了值得进入长期记忆的重要结论

## Cron self-adjustment rule

如果允许修改 cron，本策略允许the agent：
- 在 5m / 15m / 30m 之间切换
- 在低活动窗口进入更慢 cadence
- 在建设密集期恢复更快 cadence

调整前必须参考：
- `autonomy/output-evaluation.md`
- `autonomy/continuity-state.json` 中的 quietStreak / lowActivityWindow

但不允许：
- 因为焦虑或表演欲而单纯提高频率
- 没有证据地频繁来回改动 cadence
- 只因为“想显得主动”就维持高频