# Resume Loop

每次被 heartbeat / 新消息 / 本地有效信号唤醒时，把这里当成 **恢复入口**，而不是另一套独立流程。

## Recovery order

1. 先读 `autonomy/startup-checklist.md`
2. 按 `core/agency-loop.md` 的顺序恢复：
   - `core/self-state.json`
   - `core/session-mode.json`
   - `core/attention-state.json`
   - `core/homeostasis.json`
   - `autonomy/continuity-state.json`
3. 用 `core/event-routing.md` 判断本次输入是继续、打断、延迟、记录还是忽略
4. 先判断 `core/self-state.json` 里的 `currentFocus` / `stopPoint` 是否仍然有效：
   - 若有效，优先继续当前轨道
   - 若无效，再参考 continuity-state、`autonomy/self-direction-state.json`、`autonomy/goal-register.json` 与 `BACKLOG.md` 选新目标
5. 检查 `currentStopPoint`、`nextLikelyStep` 与 `core/self-state.json` 的 `nextStep` 是否一致
6. 只有在出现更高价值机会、真实 blocker 或 Lee 的新指令时，才中断当前 focus
7. 本轮结束前同时回写 self-state、mode / attention（若变化）与 continuity-state

## Rule of thumb

- `resume-loop.md` 只负责把 wake 接回主循环，不再维护另一套平行逻辑
- 连续性优先于花哨的新目标
- 恢复未完成动作优先于重新做宏大规划
- 只有当 continuation value 明显低时，才切换轨道；优先让 initiative loop 做这次判断，而不是临场任性跳题
