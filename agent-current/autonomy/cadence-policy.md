# Cadence Policy

目标：在保留自主性的同时，减少高频空转唤醒带来的噪声。

当前约束来源：`core/homeostasis.json` 决定稳态阈值，`core/session-mode.json` 决定当前运行姿态，`core/wake-model.md` 决定无 cron 的唤醒结构，`autonomy/continuity-state.json` 记录 quiet streak 与低活动窗口。

## Principle

更接近连续性，不等于每次醒来都硬做事。
当短周期内连续多次没有高价值动作时，应进入“低活动观察期”。
在 `focused` 模式下优先保持主线；在 `monitoring` / `waiting` 模式下优先降低存在感。

## Low-activity rule

如果连续 3 次自检都没有出现明显高于“安静继续”的候选动作：
- 把当前状态视为低活动窗口
- 在 `autonomy/continuity-state.json` 中显式记录 `quietStreak` 与 `lowActivityWindow`
- 必要时把 `core/session-mode.json` 切到 `monitoring` 或 `waiting`
- 后续唤醒优先只做快速筛查
- 除非出现新任务、drift、blocker 或明显高价值机会，否则保持静默

## Exit low-activity

以下任一出现时退出低活动窗口：
- Lee 有新指令
- 出现 user-facing value 候选动作
- 出现 drift，说明连续性层需要修正
- 出现明确可验证的 capability value 动作，且边际价值足够高
- `core/attention-state.json` 中出现应升级的 promoted event
