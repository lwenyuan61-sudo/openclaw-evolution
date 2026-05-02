# Continuity Thresholds

用于避免 continuity 验证本身变成伪忙碌。

## Enough evidence

满足以下任一条件时，可认为“基础 continuity 已被证明”，不必每轮都追加同类证据：
- 连续 3 轮 wake 都被判定为 resumed
- 连续 2 轮 resumed，且第三轮的动作仍明显遵守同一 stop point / focus

## After enough evidence

达到基础证据阈值后：
- 不再每轮都写 `resume-evidence.md`
- 只在出现 drift、false positive、或新模式时补证据
- 把精力转到更高价值的自主性改进，而不是重复记录同一种成功

## Escalation

若后续出现 replanned 或 drift：
- 恢复更密集的 continuity 观察
- 在 `corrections.md` 记录漂移原因
- 必要时收紧 `resume-loop` 的切换条件
