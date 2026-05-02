# Continuity Ledger

目标：作为主会话与 cron/isolated wakes 之间的统一交接页，减少连续性依赖多个分散文件造成的恢复损耗。

## Active build
- Focus: build continuity-first self-evolution with adaptive cadence, measurable output, and cron self-adjustment
- Current phase: post-08:00 consolidation has moved one step further from internal method upkeep into Lee-signal routing, so future wakes can prefer a concrete service path over reopening autonomy planning
- Why this matters to Lee: 让the agent在白天低噪声节奏里，不只会拒绝内部自转，还能在真实 Lee 信号出现时更快走到正确动作，减少打扰成本与决策摩擦

## Latest stable state
- lowActivityWindow: false
- recommendedCadence: 30m
- quietStreak: 0
- Current rule: 除非出现 Lee-facing opportunity / blocker / concrete preference signal / sustained high-value streak，否则不恢复 5m；若没有真实信号，就先用 migration checklist 拒绝新的内部方法笔记
- Latest artifact: `autonomy/lee-signal-routing-table.md`，把真实 Lee 信号分流到直接行动、偏好捕捉、阻塞提问、机会通知或保持安静，减少再次重开自治规划回路

## Required first reads on wake
1. `autonomy/continuity-state.json`
2. `autonomy/continuity-ledger.md`
3. `autonomy/identity-handoff.md`
4. `autonomy/evolution-blueprint.md`
5. `autonomy/output-evaluation.md`
6. If relevant to the current stop point, read the smallest necessary supporting artifact (for example post-0800 check / freeze gate / experiment log)

## Current stop point
现在最重要的不是再发明更多 autonomy 方法，而是验证：
- `autonomy/lee-signal-routing-table.md` 能否在下一次真实 Lee 信号出现时直接把动作路由到现有文件，而不重开大规划
- migration checklist 能否继续拦住“再补一个内部自治说明”的冲动
- cadence 维持 30m 时，是否仍足以覆盖高价值机会而不制造噪声
- 真实 Lee-facing opportunity / blocker / preference signal 出现时，是否已经有足够短的执行路径

## Next natural moves
- 后续 wakes 先检查是否有真实 Lee-facing opportunity / blocker / preference signal；有的话，优先用 `autonomy/lee-signal-routing-table.md` 路由到对应动作
- 若没有真实信号且准备做内部 artifact，先用 `autonomy/autonomy-to-service-migration-checklist.md` 打一次 yes/no 分，低分就拒绝并保持安静
- 若出现真实 Lee 偏好信号，复用 `autonomy/lee-preference-capture-prompt-stub.md`，把信号压成结构化服务规则，而不是写自由观察
- 在没有更强 leverage 前，维持 30m，避免 15m 继续制造 method-only 产物
- 每轮仍至少留下一个 artifact、明确 blocker，或一个诚实的 cadence/focus 决策

## Anti-drift note
如果某轮 wake 想切到一个全新主题，先问：
- 它是否比 currentFocus 更直接帮助 Lee？
- 它是否比继续当前 stop point 的边际价值更高？
- 如果不是，不要切。
