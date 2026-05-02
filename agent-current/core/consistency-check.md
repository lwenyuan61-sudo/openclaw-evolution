# Consistency Check

目标：在持续运行中定期检查“我是不是还是同一个我、是不是还沿着同一控制面在跑”。

## Check targets

- `core/self-state.json`
- `core/session-mode.json`
- `core/attention-state.json`
- `core/homeostasis.json`
- `core/organ-registry.json`
- `core/body-state.json`
- `core/action-state.json`
- `core/perception-state.json`
- `core/learning-state.json`
- `core/resident-config.json`
- `autonomy/continuity-state.json`

## What counts as drift

- self-state 与 continuity-state 的 currentFocus 不一致
- self-state 的 currentMode 与 session-mode 不一致
- attention slots 失控增长
- body-state 指向的器官与 organ-registry 不匹配
- perception-state 长期不更新，说明现实信号层断开
- decisionPipeline 缺少关键步骤
- resident config 缺失或与 wake model 脱节
- 连续多轮 Agency 偏低却没有学习回写、权重修正或规则修正

## Practical rule

- 在怀疑 drift、切换主线、补新器官、或连续低价值 wake 后优先跑一次自检
- 自检先于继续扩写概念
- 自检的目标是修复连接，而不是制造更多层
