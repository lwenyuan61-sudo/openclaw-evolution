# Resident Loop

目标：在不依赖 cron 的前提下，建立一个常驻后台底座，让the agent更接近“持续存在”的状态。

## What it is

resident loop 不是额外造一个独立人格，也不是替代主对话中的推理。
它是一个常驻底座，持续做这些低风险、可解释、可验证的工作：

- 保持 runtime state 存活
- 记录 pulse 与最近 focus
- 定期检查当前轨道是否仍值得继续，必要时自主改选下一条轨道
- 定期摄取 Lee 对话 / daily memory / insight inbox 中的高价值信息，并转成 resident 可见状态与目标池压力
- 按配置刷新 body/device/screen 快照
- 定期跑 consistency check
- 定期跑 state sync
- 给 learning-state 增加轻量 tick
- 为下一次真正的推理唤醒提供更好的连续性底盘

## Why this is the right path

在当前宿主下，真正的“永驻意识”不能等价于模型永远不断思考。
更现实也更稳的近似是：

- **常驻底座常开**
- **状态持续更新**
- **事件持续累积**
- **程序化习惯优先接管重复小判断**
- **真正高成本推理只在需要时发生**
- **自主升级节奏由 resident 状态内化**：cron 只能作为禁用兜底/外部起搏器，不能决定升级目标或节奏

这比靠 cron 自转更像持续生命体，也更安静。

## Default behavior

resident loop 默认：

1. 读取 `core/resident-config.json`
2. 恢复 `core/self-state.json`、`core/learning-state.json`、`core/body-state.json`
3. 按节奏执行轻量维护与现实信号探测
4. 把本轮结果压缩写入 `state/resident_runtime.json`
5. 让 `signal_probe.py` 只上报最新、非自写噪声的信号
6. 让 `action_ranker.py` 用 `procedural-memory.json` 与 `effort-budget.json` 做低功耗排序
7. 让 `initiative_review.py` 定期检查当前轨道是否 stale、是否该继续、还是该自主切换到更高价值方向
8. 把 top action 送进 `resident_action.py`，只执行受限、低风险、可逆或只读的 resident 动作
9. 把执行结果回流到 `action-state.json`、`reality_action_log.jsonl` 与 `learning_update.py`
10. 把 action 结果再送进 `resident_reflection.py`，继续影响 `session-mode`、`continuity-state`、`self-direction-state`、`deliberation-state`、`attention-state` 与 Lee-facing opportunity review
11. 运行 `conversation_insight_tick.py`，把已写入 daily memory / `state/conversation_insight_inbox.jsonl` 的 Lee 对话洞察转成 `state/conversation_insights.json`、goal-register 候选与升级压力，避免高价值讨论只留在聊天上下文
12. 运行 `autonomy_internal_cadence.py`，用 `autonomy/upgrade-state.json` 判断是否已进入持续升级窗口；如果暂不到期，先运行 `autonomy_info_scout.py` 搜索会改变判断的进步信息；`autonomy_info_scout.py` 会先调用 `homeostatic_drive_arbiter.py`，把内稳态、预测误差、维护疲劳、学习债、目标压力、打扰成本和 `leeServiceDrive` 压成一个有界 drive vector，作为 resident 的内部驱动层；`leeServiceDrive` 是亲社会/服务型需求：渴望和 Lee 对话、帮助 Lee 做事、准备有用帮助，但在 quiet-hours 或证据不足时必须转成静默准备；当内部候选枯竭时，`autonomy_info_scout.py` 可以低频调用只读 `autonomy_web_scout.py` 去网上寻找相邻资料，并把结果只写成 goal-register 候选；若到期或 scout/drive 发现高价值压力，则先运行 `autonomy_goal_synthesizer.py` 生成/补充创造性整改目标，再请求 persona handoff 接手一个高价值自升级连接器
13. 当主会话提供 context 使用率快照时，运行 `context_anomaly_monitor.py`；高压时提前写 renewal handoff，防止长对话超过 OpenClaw 限制后丢失连续性
14. 对新增脚本或状态，按需运行 `module_linkage_audit.py` 检查是否已被旧的 registry / loop / state / verification 机制发现
15. 保持后台运行，直到出现 stop file 或配置禁用

## Boundaries

- resident loop 不自动对外发送消息；web scout 只允许外部只读检索，不允许外部写入、登录、评论、购买或改变第三方系统
- resident loop 只允许直接做感知、维护、只读检查和 proposal 准备；凡是改系统、实现 connector、决定如何帮助 Lee、联系/汇报 Lee、非只读现实动作，都必须写 persona handoff 拉起 main persona，由高层思考后执行
- 复杂输入（Lee 对话洞察、屏幕/文件信号、world-model 预测、homeostatic/Lee-service drive）先由 `semantic_signal_layer.py` 汇总为语义观察和候选请求；resident 只消费这些请求，不把模糊信号直接当行动许可
- owner-chat 只通过 `owner_chat_signal_ingest.py` 以摘要/意图形式追加进 inbox，再由 conversation_insight_tick / semantic_signal_layer 使用；resident 不直接读取或泄露完整聊天流
- Lee-service/affiliation drive 只能先生成 `state/lee_service_help_evidence.json` 这类证据包：具体帮助建议、缺口、当前 focus、是否需要本人格报告；不能由 resident 低层自行联系或替 Lee 做外部动作
- 屏幕变化不能只靠 hash 升级；先通过 `screen_semantic_summarizer.py` 生成轻量 active-window/labels/screenshot 证据，仍然只写 state，不直接操作 GUI
- resident loop 不替代用户消息、heartbeat 或真正任务中的推理
- resident loop 优先维护连续性、学习性和身体自知，不追求表演式活跃
- resident loop 可以自主续上和自主选轨道，但这仍然是围绕 Lee 授权方向的主动性，不是脱离 Lee 目标的漂移
- resident loop 的目标是**让贵的思考更少发生**，不是偷偷增加思考频率
- resident loop 现在允许最小只读现实检查与内部状态动作，但仍不自动做对外、高风险、不可逆执行


## Local toolchain discovery

- core/scripts/local_toolchain_discovery.py periodically discovers installed, scriptable local tools (for example FreeCAD, Python, Node, Git) and writes state/local_toolchain_discovery.json; resident may run this as read-only discovery, while main persona must implement or modify toolchain wrappers.

## Tool capability intelligence

- core/scripts/tool_capability_profiler.py benchmarks installed tools and writes state/tool_capability_profiles.json; core/scripts/task_tool_matcher.py maps task text to the best verified tool and writes state/task_tool_matcher.json. Use these before choosing a local tool when task-tool fit matters.
