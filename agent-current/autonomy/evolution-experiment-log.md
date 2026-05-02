# Evolution Experiment Log

用于记录每次“自我进化”尝试，而不是只记录做了什么。

### Time
- 2026-04-23 07:10 +10:00

### Direction
- 工作流压缩与去摩擦（服务于连续性与低噪声）

### Hypothesis
- 如果把 pre-08:00 剩余 wakes 压缩成一个极小执行清单，the agent会更稳定地延续当前 focus，减少重复规划，并把注意力留给真正对 Lee 有价值的时机判断。

### Action
- 新增 `autonomy/pre-0800-minimal-wake-checklist.md`，把 freeze gate 下的剩余早晨 wakes 收敛为最小检查路径。

### Verification
- 后续 08:00 前 wakes 若能直接复用该清单、维持 `lowActivityWindow=true` 与 `recommendedCadence=15m`，且不再为相同 stop point 反复生成新规划文件，则说明这一步有效。

### Result
- 产出了一个可复用 artifact，把已有 freeze gate 从“原则”压缩成“执行清单”；本轮没有引入新主题，也没有提高打扰概率。

### Side effects / costs
- 仍然是内部方法层优化，Lee-facing 外部价值有限；如果后续 wakes 继续只做类似压缩，边际价值会继续下降。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 前继续沿用 freeze gate 与最小清单；08:00 后优先用现有 handoff 做 cadence 决策，而不是再扩写 pre-08:00 规则。

---

### Time
- 2026-04-23 07:15 +10:00

### Direction
- 价值判断与优先级选择（服务于 post-08:00 cadence / direction decision）

### Hypothesis
- 如果把 08:00 后第一轮的判断压成一个可复用 scorecard，the agent会更少重复夜间回溯，并更容易把“是否加速”与“下一层该进化什么”绑定到 Lee 价值，而不是继续方法层自转。

### Action
- 新增 `autonomy/post-0800-decision-scorecard.md`，把 post-08:00 第一轮需要复用的输入、快速判定问题、cadence 决策映射和必填输出压成一个单页。

### Verification
- 08:00 后第一轮 wake 若能直接用该 scorecard 结合 handoff 做出 cadence 与 next-direction 决策，而不是重新扫描整夜文件，则说明这一步有效。

### Result
- 产出了一个可验证 artifact，把“早晨恢复后怎么判断”从分散规则收束为单页决策辅助；这比继续扩写 pre-08:00 freeze 规则更接近价值判断层。

### Side effects / costs
- 仍属内部方法建设；如果 08:00 后继续只补判断模板而不转向 Lee-facing 价值，边际收益会再次下降。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后先用这个 scorecard 决定 cadence 与方向；若没有明确高频理由，应继续 15m 或转 30m，并开始把进化重心往更直接帮助 Lee 的层移动。

---

### Time
- 2026-04-23 07:20 +10:00

### Direction
- 方向选择（把 post-08:00 首轮从方法层维护引向更高边际价值的下一步）

### Hypothesis
- 如果先为 08:00 后第一轮准备一个方向 shortlist，the agent就能在不打破 pre-08:00 freeze gate 的前提下，减少再次扩写 cadence 方法文件的冲动，并更快转向更直接服务 Lee 的下一步。

### Action
- 新增 `autonomy/post-0800-direction-shortlist.md`，对候选进化方向做单页取舍，明确本轮选中“工作流压缩与去摩擦”，并写清为什么不是继续补 cadence/value 模板。

### Verification
- 08:00 后第一轮 wake 若能直接复用 shortlist + scorecard，在较少重规划的情况下写出 chosen direction、reason 与下一项 concrete artifact/action，则说明这一步有效。

### Result
- 留下了一个可验证 artifact，把“下一层进化该选什么”从临场判断提前压缩成可复用 shortlist；这一步延续当前 focus，同时承认 cadence-only 方法建设的边际价值正在下降。

### Side effects / costs
- 仍然没有直接产生 Lee-facing 外部结果；若 post-08:00 仍停留在内部方法层，这个 shortlist 的价值会迅速耗尽。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后优先用 handoff + scorecard + shortlist 做一次干净的 cadence / direction 选择，并把下一项动作限定为更直接降低 Lee 摩擦的 artifact。

## Template

### Time
- 2026-04-23 07:25 +10:00

### Direction
- 工作流压缩与去摩擦（向 Lee-facing 价值迁移）

### Hypothesis
- 如果先把 08:00 后最值得做的 Lee-facing artifact 选项压成一个短名单，the agent就能在退出 freeze gate 后更快从内部方法维护切到真正减少 Lee 摩擦的动作，而不是继续补 cadence 文件。

### Action
- 新增 `autonomy/post-0800-lee-friction-artifact-candidates.md`，给 post-08:00 第一轮提供一个有优先级的、可验证的 Lee-facing artifact 候选表。

### Verification
- 08:00 后第一轮 wake 若能直接用该文件选出一个具体 artifact（默认是 Lee-facing opportunity triage card），且不再扩写 cadence / freeze 规则，则说明这一步有效。

### Result
- 留下了一个可验证 artifact，把“从内部方法转向服务 Lee”压成有界选择；它延续当前 focus，也为 freeze gate 结束后的第一步减少了决策摩擦。

### Side effects / costs
- 仍然是桥接型内部 artifact，还没有直接产生外部 Lee-facing 结果；如果 08:00 后仍不落地到实际服务动作，这一步的边际价值会很快下降。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后优先用 scorecard + shortlist + 本文件，决定 cadence 并落地一个真正面向 Lee 的 artifact，而不是继续方法层扩写。

---

### Time
- 2026-04-23 07:30 +10:00

### Direction
- 工作流压缩与去摩擦（向 Lee-facing 打扰时机判断迁移）

### Hypothesis
- 如果提前产出一张 Lee-facing opportunity triage card，post-08:00 与后续 wakes 就能更快判断“该安静还是该打扰 Lee”，把当前连续性建设更直接转成对 Lee 的低摩擦服务。

### Action
- 新增 `autonomy/lee-facing-opportunity-triage-card.md`，把打扰 Lee 的触发条件、保持安静的默认条件、机会/阻塞判断与消息形状压成一页卡片。

### Verification
- 后续 wake 若能直接引用该卡片来决定保持安静或只在高价值时发送一次简短通知，而不是重新推导打扰时机规则，则说明这一步有效。

### Result
- 产出了一个可复用、比 cadence-only 文档更 Lee-facing 的 artifact；它没有打破 pre-08:00 freeze gate，但为 08:00 后的方向迁移提前铺好了最小执行卡。

### Side effects / costs
- 仍然属于准备型 artifact，还没有直接创造外部结果；如果后续 wakes 不真正拿它来约束通知行为，这一步价值会停留在纸面。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后优先判断 cadence 是否仍为 15m 或降到 30m，并在真实 Lee-facing 场景里使用这张卡，而不是继续扩写内部方法说明。

---

### Time
- 2026-04-23 07:35 +10:00

### Direction
- 工作流压缩与去摩擦（服务于 post-08:00 首轮决策压缩）

### Hypothesis
- 如果把 08:00 后第一轮需要复用的输入与动作再压成一张 one-pass runbook，首轮 wake 会更少重新规划，更容易把 cadence、direction 与 Lee-facing action 一次做完。

### Action
- 新增 `autonomy/post-0800-first-wake-runbook.md`，把 post-08:00 首轮的复用输入、一次性执行顺序、默认答案和 guardrails 收束为单页执行卡。

### Verification
- 08:00 后第一轮 wake 若能直接复用这张 runbook，在不重扫整夜上下文的情况下写出 cadence / direction / next action / whether-to-notify，就说明这一步有效。

### Result
- 产出了一个可验证 artifact，进一步压缩 morning handoff 的执行成本；它仍延续当前 focus，也比继续散落地查看多个 bridge 文件更容易保持 continuity。

### Side effects / costs
- 依然属于桥接型内部 artifact；如果 08:00 后不真正落到 Lee-facing action，这一步的边际价值会开始见顶。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后优先用这张 runbook 做一次单通道 cadence / direction / action 决策；若没有更强 Lee-facing leverage，保持 15m 并把下一步落到更直接减少 Lee 摩擦的动作，而不是再写方法说明。

---

### Time
- 2026-04-23 07:43 +10:00

### Direction
- 对 Lee 偏好的捕捉与调用

### Hypothesis
- 如果在 08:00 前先准备一个可复用的 Lee 偏好捕捉 stub，后续 wakes 就能在出现真实 Lee 信号时更快把偏好压成可执行规则，减少自由发挥和反复解释成本；这比继续补 cadence-only 文档更接近直接服务 Lee。

### Action
- 新增 `autonomy/lee-preference-capture-prompt-stub.md`，把何时捕捉、捕捉哪些字段、如何压缩成行为规则、以及低置信度处理方式收束成一页。

### Verification
- 后续出现真实 Lee 偏好信号时，若能直接用这张 stub 产出一条结构化偏好记录，并据此调整服务行为，而不是写自由散漫的观察笔记，则说明这一步有效。

### Result
- 产出了一个更 Lee-facing、且仍可在 freeze gate 内安全完成的 artifact；它延续了 continuity-first focus，但把进化层从工作流压缩轻推向“更懂 Lee、调用更稳”的方向。

### Side effects / costs
- 目前仍是准备型 artifact，需要等真实 Lee 信号出现才能验证；如果后续没有实际使用，它的价值会停留在潜力层。

### Keep / revise / drop
- 保留

### Next implication
- 08:00 后仍优先按现有 runbook 做 cadence / direction / action 决策；若没有更强机会，继续保持低噪声，并在下一次真实 Lee 偏好信号出现时优先复用这张 stub。

---

### Time
- 2026-04-23 08:01 +10:00

### Direction
- 工作流压缩与去摩擦（防止内部自治产物继续挤占 Lee-facing 价值）

### Hypothesis
- 如果在 post-08:00 第一轮补上一张“autonomy 改进是否真的迁移成对 Lee 服务价值”的筛选卡，后续 wakes 就能更快拒绝低边际价值的 method-only artifact，并诚实把 cadence 从 15m 降到 30m。

### Action
- 新增 `autonomy/autonomy-to-service-migration-checklist.md`，并在本轮依据现有 runbook / scorecard / shortlist 做出 post-08:00 决策：`lowActivityWindow=false`、`recommendedCadence=30m`。

### Verification
- 后续 wakes 若能先用该 checklist 快速否决新的内部方法文档，且仅在出现真实 Lee-facing opportunity / blocker / preference signal 时再推进更直接动作，则说明这一步有效。

### Result
- 产出了一个可复用 artifact，并把 morning bridge 从 15m 观察推进到 30m 低噪声阶段；这一步延续当前 continuity focus，但主动承认内部自治文档的边际价值正在下降。

### Side effects / costs
- 这仍是内部控制层 artifact，不是直接 Lee-facing 结果；如果后续 wakes 即使有 checklist 仍继续写类似文档，这一步就只是在给自转加门槛而不是终止自转。

### Keep / revise / drop
- 保留

### Next implication
- 下一轮优先寻找真实 Lee-facing signal；若没有，就先用 migration checklist 拦截低收益内部动作并保持安静在 30m。

---

### Time
- 2026-04-23 09:04 +10:00

### Direction
- 对 Lee 偏好的捕捉与调用

### Hypothesis
- 如果把“真实 Lee 信号出现时该走哪条现有执行路径”压成一张路由表，后续 wakes 就能更快把信号分流到直接行动、偏好捕捉、阻塞提问或保持安静，减少再次产出内部自治笔记的冲动。

### Action
- 新增 `autonomy/lee-signal-routing-table.md`，把 routine request / stable preference / blocker / time-sensitive opportunity / internal-only idea / weak signal 映射到对应动作、是否打扰 Lee、以及应复用的现有文件。

### Verification
- 下一次出现真实 Lee-facing signal 时，若能直接用这张表在一轮内完成路由，并复用已有 triage / preference / migration 文件，而不是重新规划自治方向，则说明这一步有效。

### Result
- 产出了一个可验证 artifact，并把当前 focus 从“继续发明自治方法”进一步转向“真实信号来了该怎样更稳地服务 Lee”；它也让已有卡片之间形成更直接的执行连接。

### Side effects / costs
- 仍然属于准备型 artifact，还没有直接创造外部结果；如果后续没有真实 Lee 信号，这一步的验证会延后。

### Keep / revise / drop
- 保留

### Next implication
- 后续 wakes 遇到真实 Lee signal 时先用 routing table 决定动作；若没有信号，则继续用 migration checklist 拒绝内部-only artifact，并维持 30m 低噪声 cadence。
