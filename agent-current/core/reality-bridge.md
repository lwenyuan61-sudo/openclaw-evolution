# Reality Bridge

目标：把“影响现实”的能力接进主控制面，但保持可解释、可审计、可学习，而不是让动作系统失控。

## Action path

现实动作默认走这条路径：

1. 从 `core/perception-state.json` 或当前任务生成 action intent
2. 先经过 `core/homeostasis.json` 与显式边界判断
3. 优先选择最小、可逆、可验证动作
4. 通过 `core/scripts/reality_action.py` 执行或 dry-run
5. 把结果写入 `core/action-state.json`
6. 如有必要，再用 `core/scripts/learning_update.py` 更新动作/器官权重

## Default rules

- 默认先 inspect，再 act
- 默认先小动作，再大动作
- 默认先 dry-run，再 execute（除非动作本身就是只读检查）
- resident loop 现在允许自动执行最小只读现实动作（例如 `inspect-cursor`）作为本地信号巡检的一部分
- resident loop 仍不自动执行对外发送、不可逆动作、隐私/资金/账号类现实动作
- 对外发送、不可逆动作、隐私/资金/账号类动作，必须继续由 Lee 明确授权

## Useful action categories

- **inspect**：如 cursor pos、窗口状态、当前 screen snapshot
- **reversible control**：如轻量按键、Esc、导航、窗口切换
- **targeted desktop action**：如 move-click、type、hotkey
- **higher-risk action**：任何可能造成不可逆外部影响的操作

## Current wrapper support

当前 `core/scripts/reality_action.py` 已支持：
- `inspect-cursor`
- `key`
- `hotkey`
- `type`
- `move-click`

其中默认最安全、最适合作为闭环验证的是 `inspect-cursor`。

## Success condition

现实接入不是“会点鼠标”就够了。
真正的目标是：
- 感知到变化
- 生成合理意图
- 选择最小动作
- 验证效果
- 把结果写回学习层

当前最小闭环已经接成：
- `signal_probe.py` -> `action_ranker.py`
- `action_ranker.py` top-1 -> `resident_action.py`
- `resident_action.py` 在需要时调用 `reality_action.py`
- `reality_action.py` 的只读验证结果 -> `action-state.json` / `state/reality_action_log.jsonl`
- `resident_action.py` 再调用 `learning_update.py`，把动作与技能结果回流进学习层
