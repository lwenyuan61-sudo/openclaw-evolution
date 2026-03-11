# 清理模式 A（保守）

已执行：
- 禁用 brainflow-bridge（不再自动接管/自动回复 WhatsApp）
- brainflow 后台只写 outbox，不做最终价值判断

未删除（保留以便回滚/对比）：
- hooks/brainflow-bridge 源码
- breakthrough_gate 等旧插件

后续若确认稳定，可将未使用内容移入 brainflow/_archive/（而不是硬删除）。
