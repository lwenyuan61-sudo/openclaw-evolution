# Event Routing

把不同来源的输入统一成事件，再决定它们应停留在观察、走习惯层、还是升级到深推理层。

## Event classes

### 1. direct-user
来源：Lee 的直接消息或明确命令
- 默认优先级：最高
- 是否可打断 currentFocus：是
- 默认动作：立即响应或执行
- 默认层级：直接进入 S2，然后按需要落回 S1/S0 执行

### 2. user-blocker
来源：需要 Lee 决策的 blocker、边界问题、不可逆动作前确认
- 默认优先级：最高
- 是否可打断 currentFocus：是
- 默认动作：尽快提出清晰问题
- 默认层级：S2

### 3. heartbeat
来源：例行 wake
- 默认优先级：中
- 是否可打断 currentFocus：否，除非发现高价值机会或 drift
- 默认动作：继续 currentFocus、快速筛查、或做一个最小真实动作
- 默认层级：先从 S0/S1 开始，只有满足升级条件才进 S2

### 4. manual-maintenance
来源：明确触发的维护、自检、轻量复盘
- 默认优先级：中低
- 是否可打断 currentFocus：通常否
- 默认动作：静默推进、记录、整理
- 默认层级：S0/S1，必要时短暂进入 S3

### 5. local-signal
来源：屏幕变化、文件变化、设备状态、camera/audio 事件
- 默认优先级：视价值而定
- 是否可打断 currentFocus：仅当与 Lee 的当前利益强相关或具时效性
- 默认动作：先参考 `core/perception-state.json`、`core/body-state.json` / `core/organ-registry.json` 判断哪种器官可用，再归档、验证或生成最小现实动作意图
- 非屏幕信号门：`workspace-changed` / artifact / device 类信号先用 path、old/new content hash、artifact kind、textReadable、size 和 provenance 建立身份；只有具备 artifact diff / preview / user-change 证据，或与 currentFocus / Lee 目标明确相关时，才进入 opportunity triage / S2。自写回与设备回响默认留在 S0/S1。
- 默认层级：先 S0 取样，再 S1 复用习惯，不够时升 S2

### 6. internal-idea
来源：内部想法、方法改进、结构优化冲动
- 默认优先级：最低
- 是否可打断 currentFocus：否
- 默认动作：只有在 currentFocus 明确相关时才执行，否则记入 openLoops 或忽略
- 默认层级：通常停留在 S0/S3，不轻易占用 S2

### 7. persona-handoff
来源：`state/persona_deliberation_handoff.json` 中由 resident / S2 写出的 pending 接手请求
- 默认优先级：高于普通 heartbeat，低于 direct-user
- 是否可打断 currentFocus：仅当它本身就属于 currentFocus 的自然续篇，或明确被判断为高 Lee 价值机会
- 默认动作：由the agent本人格在当前连续性上下文里接手，而不是重新当成陌生任务解释一遍；若尚未 claim 或 claim 已 stale，先 claim 再继续；若 handoff 明确写出 `shouldReportToLee=true`，则默认在同一次 wake 中向 Lee 发简短结果汇报，并把“已汇报”写回 handoff 状态
- 默认层级：S2 或 S3，视 handoff 中的问题与证据而定

## Promotion rules

默认可以参考 `core/scripts/action_ranker.py` 与 learning-state 中的 event 权重，但统计层只做加权建议，不覆盖显式边界。

只有满足以下任一条件，事件才从记录/观察升级：

- 直接帮助 Lee
- 显著减少未来摩擦
- 修复已知缺陷或连续性 drift
- 与 currentFocus 高度一致，且验证成本低
- 时效性高，错过就失去价值
- 现有 habit 无法解释或处理
- 需要跨时间整合多条证据
- 需要多步工具调用才能查清或完成
- 多目标冲突，需要明确取舍

## Deep-reasoning triggers

满足以下任一条件时，允许从 S1 升级到 S2：

- 新颖性高：第一次遇到的模式或解释缺口明显
- 不确定性高：两种以上解释都合理，且会影响行动
- 工具链需求：只靠口头推断不够，需要 read / inspect / execute / verify 链
- 现实影响前置：准备从感知走向最小现实动作，需要额外核实
- Lee-facing opportunity triage：可能值得打扰 Lee，但还需要证据与判断
- persona handoff pending：脚本层已经把机会/疑难压缩成待本人格接手的问题，需要保持同一人格继续完成

## Suppression rules

以下情况默认不升级：

- 只是会产生新的内部说明文档
- 对 Lee 没有可见收益
- 需要打断更重要的当前主线
- 和最近刚做过的检查重复
- 只是 resident/self 写回造成的工作区变化
- 只是为了显得主动
