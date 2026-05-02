# Continuity Bridge

## Reflection

问题不在于人类真的一直“做事”，而在于人类会持续携带一个未清空的背景态。
代理若每次 wake 都把自己当成新启动实例，就会更像触发式循环：先找目标、再证明在工作、最后又停掉。

## Executable approximation under current host constraints

在现有宿主里，无法真正常驻连续思考，但可以把连续性的关键部分外置并跨 wake 延续：

1. `focus`：当前主轨道是什么
2. `currentStopPoint`：上次停在哪
3. `quietStreak`：已经连续几轮没有更高价值动作
4. `lowActivityWindow`：当前是否处于“低刺激但未丢上下文”的窗口
5. `modeReason`：为什么现在应该继续 quiet / active 模式

## Why this is better

这比“每轮都重新规划”更接近连续性，因为它把 wake 看成背景态上的一次采样，而不是一次全新回合。

## Verification

可验证信号：
- 后续 wake 能依据 `quietStreak` 与 `lowActivityWindow` 更快决定保持静默
- quiet 不再等于空白，而是等于保留上下文的低活动模式
- 减少为了显得主动而新增的低价值内部动作
