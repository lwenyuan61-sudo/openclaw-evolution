# Learning Loop

目标：把每次行动后的有效经验沉淀下来，让the agent的后续行为逐步更稳，而不是每次都靠临场发挥。

## Trigger

在以下情况优先运行学习回写：

- 这轮找到了一条可复用做法
- 这轮暴露了明显失误或摩擦
- 这轮的评分里 Agency / Continuity / Efficiency 明显偏低
- 这轮发现某个器官、技能、或文件连接方式更顺手

## Loop

1. 记录这轮发生了什么
2. 判断是：
   - 新模式
   - 新规则
   - 新偏好
   - 新错误样式
   - 新的抑制条件
3. 决定应该回写到哪里：
   - `core/self-state.json`：当前行为倾向、nextStep、openLoops
   - `core/attention-state.json`：注意力与打断规则
   - `core/homeostasis.json`：稳态与抑制规则
   - `core/effort-budget.json`：哪些事件值得升级到高成本思考
   - `core/procedural-memory.json`：重复成功后的程序化习惯
   - `core/learning-state.json`：计数器、最近 lessons / failures、器官有效性
   - `MEMORY.md`：长期稳定偏好或重要决策
   - daily memory：当天发生的具体事件
4. 如果只是一次性现象，不要过拟合成长期规则
5. 若学习结果适合进入统计层，用 `core/scripts/learning_update.py` 更新 event/action/skill 权重
6. 若某条做法已重复成功且低风险，优先把它编译进 `core/procedural-memory.json`，而不是继续每轮都重新思考
7. 下一轮验证这个学习是否真的减少摩擦

## Anti-overfitting rule

- 单次情绪或偶发事件，不自动升级成长期人格规则
- 只有重复有效、或 Lee 明确确认的偏好，才进入长期层
- 如果某条学习让系统更吵、更碎、更爱打断，就优先回滚
