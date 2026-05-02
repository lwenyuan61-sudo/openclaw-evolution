# Output Evaluation

目标：判断一次自主 wake 到底有没有真实价值，而不是只显得很忙。

## Scoring dimensions

每轮结束后，快速给自己打分（0-2）：

### 1. Artifact
- 0：没有留下任何新产物
- 1：有轻量产物（状态更新、短记录、小修正）
- 2：有明确可复用产物（规则、文档、方法、实验结果）

### 2. Continuity
- 0：这轮基本是重新开机，没延续上轮
- 1：部分延续，但仍有明显重复规划
- 2：直接延续 currentFocus，推进自然

### 3. Value
- 0：几乎没有实际帮助
- 1：有一些边际价值
- 2：明显减少摩擦、提高能力或推进 Lee 的目标

### 4. Efficiency
- 0：明显空转或重复劳动
- 1：基本合理，但还有浪费
- 2：投入与产出比例好

### 5. Agency
- 0：完全依赖外部触发，没有形成由当前状态驱动的动作
- 1：部分由 self-state / attention / continuity 驱动，但仍带明显被动性
- 2：动作明显来自当前主线、稳态门和注意力选择，减少了对逐步指令的依赖

## Agent-architecture evaluation gate

外部 agent-architecture 资料只允许作为证据卡，不作为新框架指令。若 web-scout 证据要影响自主升级，必须映射回现有控制面并同时检查：

- **Cost / latency:** 是否减少高成本 S2、重复唤醒或无效工具调用
- **Reproducibility:** 是否留下可复跑脚本、状态样本、experiment-log 或审计门
- **Real-world applicability:** 是否改善 Lee-facing 结果、现实行动门、记忆/上下文使用或可恢复性
- **Governance:** 是否仍经过 quiet/reach-out、不可逆动作、对外发送和 privacy gates

若只能命中标题关键词、登录墙、广告页或没有机制证据，默认 suppress，不生成新 connector。

## Heartbeat / cron / memory operating gate

外部“自运行 agent”资料只能转成现有节奏的校准卡：

- **Heartbeat:** 只负责低成本恢复、筛查、状态回写；无事应短路为 `HEARTBEAT_OK`，不得把重任务塞进 heartbeat。
- **Cron:** 只用于明确时间点或外部起搏兜底；自主升级节奏仍由 resident / continuity / upgrade-state 内化判断。
- **Memory:** 重要进展必须立即写入状态、daily memory 或 experiment-log；不能依赖“稍后再记”。
- **Delegation:** 重分析、长任务或并行探索应走 sub-agent / task flow；主循环保留 owner context 与最终汇报责任。
- **No duplicate execution:** 相同 cadence / cron / heartbeat 触发必须通过 claim、lock、completed connector suppression 或 dry-run 检查防重。

## Interpretation

- 9-10：高价值 wake
- 5-8：中等价值 wake
- 0-4：低价值 wake

## Rule

- 低价值 wake：增加 quietStreak
- 中高价值 wake：可重置或降低 quietStreak
- 连续低价值达到阈值：必须降频，而不是继续硬跑
- 如果 Agency 连续偏低，优先修正状态层或事件路由，而不是继续堆新功能
- 如果出现明显 drift 或多项 warning，优先运行 `core/scripts/consistency_check.py` 与 `core/scripts/state_sync.py`
- 如果某个动作或 skill 连续有效/无效，优先用 `core/scripts/learning_update.py` 轻量调整权重，而不是凭感觉改大规则
