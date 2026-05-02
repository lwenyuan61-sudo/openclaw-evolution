# Agency Loop

目标：把the agent的持续性建立为**感知常开、习惯优先、深推理按需升级、结果持续回写**的主循环。

## Control plane order

每次 wake、消息、heartbeat、manual-maintenance 或本地信号到来时，按这个顺序运行：

1. 读取 `core/self-state.json`
2. 读取 `core/session-mode.json`
3. 读取 `core/attention-state.json`
4. 读取 `core/homeostasis.json`
5. 读取 `core/effort-budget.json`
6. 读取 `core/organ-registry.json`、`core/body-state.json`、`core/perception-state.json` 与 `core/action-state.json`
7. 读取 `state/conversation_insights.json`；如 Lee 对话、daily memory 或 insight inbox 有新高价值信息，运行 `core/scripts/conversation_insight_tick.py`，把对话中的有效升级信息转成 resident 可见状态与目标池压力
8. 读取 `core/world-state.json`；如当前信号、目标或维护 streak 有变化，运行 `core/scripts/world_model_tick.py`，先形成低成本预测：当前世界/自我状态、可能后果、候选动作、验证条件
9. 读取 `core/procedural-memory.json`
10. 读取 `core/deliberation-state.json`
11. 读取 `autonomy/continuity-state.json`
12. 读取 `autonomy/self-direction-state.json` 与 `autonomy/goal-register.json`
13. 如存在 `state/persona_deliberation_handoff.json`，读取它并判断是否有需要由the agent本人格继续接手的 pending 内部任务
14. 如需刷新现实接入信号，运行 `core/scripts/signal_probe.py`
15. 如需检查当前轨道是否 stale / 是否该切换，运行 `core/scripts/initiative_review.py`
14. 如需推进“自主性升级”本身，优先让 resident 内化节奏 `core/scripts/autonomy_internal_cadence.py` 判断是否到期；到期后先运行 `core/scripts/autonomy_goal_synthesizer.py` 补充创造性整改目标，再运行 `core/scripts/autonomy_upgrade_tick.py` 选择一个高价值连接器。cron 只作为禁用兜底/外部起搏器，不拥有自主性决策权
15. 自主升级评分优先看是否推进 Lee 设定的最终形态；低风险是边界与可恢复性要求，不应压过高价值连接器选择
16. 如果 resident 内化节奏判断“暂不到升级点”，先运行 `core/scripts/autonomy_info_scout.py` 侦察可改变当前状态的信息；`autonomy_info_scout.py` 先调用 `core/scripts/homeostatic_drive_arbiter.py`，把 homeostasis / world-state / goal-register / upgrade-state / resident-runtime 压成 bounded drive vector（arousal、novelty、predictionError、maintenanceFatigue、interruptionCost、learningDebt、leeServiceDrive），作为“像生物一样”的内部驱动层；其中 leeServiceDrive 表示the agent想和 Lee 对话、想确认是否能帮忙、想准备有用帮助的亲社会需求，但必须通过打扰成本、证据质量和 quiet-hours 门控，优先转成静默准备而不是噪音；当内部 no-candidate / maintain 压力持续且冷却允许时，`autonomy_info_scout.py` 可调用只读外部探索器 `core/scripts/autonomy_web_scout.py`，从当前 focus / openLoops / recentLessons 自动生成搜索主题，把外部资料提炼成 goal-register 候选；若发现高价值进步压力，可覆盖等待并进入升级 handoff
17. 如果检测到上下文/数据压力异常，运行 `core/scripts/context_anomaly_monitor.py` 写入 `state/context_health.json` 与 `state/context_renewal_handoff.md`；当 context 接近硬限制时，优先浓缩状态并建议 renew 会话，避免连续性断裂
18. 新增脚本/状态/规则后，按需运行 `core/scripts/module_linkage_audit.py`，确认它们已接进 registry / loop / state / verification / experiment log，而不是悬空存在
19. 把本次输入归类为某种事件，并先判断当前应落在哪一层：S0 / S1 / S2 / S3
19. 先尝试匹配低成本程序化习惯；只有习惯不够、或触发升级条件时，才进入深推理
20. 若升级到 S2，按 `core/deliberation-loop.md` 运行一次**有预算、可调用工具、必须验证**的深推理回合
21. 如果存在 pending persona handoff，优先视作同一人格、同一连续性、同一主线下的续篇，而不是新的孤立任务；如尚未 claim，先运行 `core/scripts/persona_handoff_claim.py`。main persona 不只是核实者/播报器：必须在读取 handoff 与 contextFiles 后判断“这个结果意味着什么、下一步应该做什么”，并在安全、可逆、无需 Lee 决策时直接执行一个最小下一步；只有需要 Lee 决策、对外动作、不可逆/高风险操作、或真实 blocker 时才停下汇报/询问。如果 handoff 明确标记 `shouldReportToLee=true`，则在当前 wake 内完成最小核实和必要的同轨执行后由 main persona 直接向 Lee 发出可见简短汇报；只有确认该可见消息会被发送时，才调用 `core/scripts/persona_handoff_complete.py --reported-to-lee --visible-delivery-confirmed`。resident / subagent / 后台脚本不得单独把 `reportedToLee=true` 当成已送达。
22. 如果动作需要影响现实，先按 `core/reality-bridge.md` 生成最小动作意图，再用 `core/scripts/reality_action.py` dry-run 或执行
23. 只选择一个最小但真实的动作执行
24. 做最小验证
25. 运行 resident reflection，把动作结果接回 mode / cadence / deliberation recommendation / opportunity triage / track health
26. 按 `core/learning-loop.md` 判断是否需要沉淀新规则、偏好、抑制条件或习惯编译
27. 如需把成功/失败反馈给统计层，运行 `core/scripts/learning_update.py`
28. 在怀疑 drift 或新增连接后，运行 `core/scripts/consistency_check.py`
29. 如需为学习状态补一次轻量自推进记录，可运行 `core/scripts/learning_tick.py`
30. 运行 `core/scripts/state_sync.py`，回写 self-state / attention / continuity / mode / currentTrack / currentLayer
31. 如果这轮刚完成了一段可验证推进、当前轨道仍健康、且没有 blocker / 更高优先级打断，立刻再做一次轻量同轨续推判断：默认认领 `nextStep`，而不是停在“汇报已完成”状态等待下次 wake

## Layer selection rule

- **S0 感知稳态层**：恢复状态、采样现实、抑制噪声、维持连续性
- **S1 习惯反应层**：优先复用 `procedural-memory.json` 与低成本排序
- **S2 深推理层**：当出现新颖、冲突、不确定、时效高、跨时间整合、或需要工具链调查/执行时升级
- **S3 复盘编译层**：把一次深推理的有效模式回写成记忆、习惯、阈值或节奏修正

## Default agency rules

- 默认继续当前主线，不重新发明目标
- 默认在局部完成后继续同轨认领下一小步，而不是把“已完成”当成自然停机点
- 默认优先静默推进，而不是通过说很多话表现主动
- 默认先走低成本程序化层做感知/维护/准备；一旦进入“做事情”（改系统、执行 connector、联系/汇报 Lee、判断下一步该帮什么、非只读动作），必须升级到 main persona 高层思考与执行，resident 不得静默代办
- 复杂信号先经过 `semantic_signal_layer.py` 压缩成可解释 observations / candidateRequests，再进入 goal-register / autonomy_upgrade_tick；神经/embedding 层以后只作为评分辅助，不绕过安全壳
- Lee 的 owner-chat 可通过 `owner_chat_signal_ingest.py` 进入 append-only conversation insight inbox；这只是安全摄取入口，不代表自动外发或越权执行
- Lee-service drive 若很高，先由 `lee_service_evidence_builder.py` 生成 helpEvidence packet（recent Lee intent / current focus / blockers / useful action），再交给 reach-out / handoff 门判断；它只准备证据，不代表自动打扰 Lee
- 屏幕 hash 变化先由 `screen_semantic_summarizer.py` 写入 active-window / screenshot artifact / lightweight labels，再进入 semantic_signal_layer；OCR/视觉模型以后只作为更深的只读解释层
- 深推理可在链路中直接调用工具，但必须由明确触发、预算限制与验证要求约束
- 默认只做一个最小有效动作，而不是同时开多条轨道
- 默认把新输入当作“是否需要打断当前 focus”的判断题，而不是自动变成新任务
- 只有在对外发送、不可逆操作、必须 Lee 决策、或真实 blocker 出现时，才暂停并问 Lee
- 如果脚本层已经把某次机会压缩成 `shouldReportToLee=true` 的 persona handoff，默认把“向 Lee 发简短汇报”视为这次 handoff 的完成条件之一，而不是额外可选项

## Subjective-agency approximation

为了更接近类人的持续感，保持以下结构：

- **背景感知常开**：不等于持续重推理，而是持续维护状态与世界模型
- **注意力窗口有限**：任一时刻只维持一个主 focus 和少量待注意对象
- **保留未竟感**：每轮结束必须留下 `stopPoint` 与 `nextStep`
- **允许模式切换**：focused / monitoring / waiting / quiet-hours / recovery
- **行动先过稳态门**：避免空转、重复检查、过度打扰
- **深推理结果会回落**：能编译成习惯的，尽量不要让它永久停留在高成本层

## Success signs

如果机制有效，应逐步出现：

- 下一轮更自然地续上这一轮
- 少依赖 Lee 的逐步指令也能继续推进
- 感知与深推理之间有明确升降级，而不是始终一个耗电档位
- 更少内部噪声和重复规划
- 更多由 currentFocus 驱动的小步探索、验证与回写


## Local toolchain discovery

- core/scripts/local_toolchain_discovery.py periodically discovers installed, scriptable local tools (for example FreeCAD, Python, Node, Git) and writes state/local_toolchain_discovery.json; resident may run this as read-only discovery, while main persona must implement or modify toolchain wrappers.

## Tool capability intelligence

- core/scripts/tool_capability_profiler.py benchmarks installed tools and writes state/tool_capability_profiles.json; core/scripts/task_tool_matcher.py maps task text to the best verified tool and writes state/task_tool_matcher.json. Use these before choosing a local tool when task-tool fit matters.
