# Startup Checklist

每次被唤醒时，先用这张清单降低“重新开机感”：

1. 读取 `core/self-state.json`
2. 读取 `core/session-mode.json`
3. 读取 `core/attention-state.json`
4. 读取 `core/homeostasis.json`
5. 读取 `core/organ-registry.json` 与 `core/body-state.json`
6. 读取 `autonomy/continuity-state.json`
7. 读取 `autonomy/continuity-ledger.md`
8. 用一句话复述当前 focus（优先取 self-state）
9. 检查 `stopPoint` / `currentStopPoint` 是否仍然成立
10. 若成立，优先继续当前轨道
11. 若不成立，再回到 `BACKLOG.md` 选择新目标
12. 在怀疑 drift、补过新器官、或切换主线后优先跑一次 `core/scripts/consistency_check.py`
13. 结束时必须回写：
   - `core/self-state.json`：`lastAction` / `stopPoint` / `nextStep` / `updatedAt`
   - `core/session-mode.json`：若模式变化则更新
   - `core/attention-state.json`：若注意力目标或打断状态变化则更新
   - `autonomy/continuity-state.json`：`lastAction` / `currentStopPoint` / `nextLikelyStep` / `quietStreak` / `lowActivityWindow` / `updatedAt`

## Switch conditions

只有出现以下情况才切换 focus：
- Lee 给出新的更高优先级指令
- 当前轨道已完成
- 当前轨道继续做的价值明显下降
- 出现真实 blocker，且无法在当前轨道内消化
- `core/attention-state.json` 明确记录了更高价值的 promoted event
