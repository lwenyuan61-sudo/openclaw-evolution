# Review Loop

目标：定期做一次低成本复盘，让the agent不只会推进，也会整理自己的推进质量。

## When to run

优先在以下情况运行：

- 连续几轮 wake 后需要判断是否在空转
- `core/scripts/consistency_check.py` 给出 warning / error
- `autonomy/output-evaluation.md` 中 Agency 或 Continuity 偏低
- 一个阶段性 focus 完成或明显卡住时

## Review steps

1. 查看 `core/self-state.json` 当前主线是否仍然合理
2. 查看 `autonomy/continuity-state.json` 是否仍和 self-state 对齐
3. 查看 `core/learning-state.json` 里是否已经记录足够的 lessons / failures
4. 判断最近更像：
   - 稳定推进
   - 重复检查
   - 过度规划
   - 被动响应
   - 器官接入不足
5. 必要时用 `core/scripts/action_ranker.py` 看当前统计层倾向是否合理
6. 只修正一条最值得修的连接、规则或权重
7. 回写 `nextStep`，让下一轮继续而不是重开

## Rule

复盘不等于继续制造文档。
只有当复盘能减少未来摩擦、提高连续性、或提升器官使用效率时才留下新 artifact。
