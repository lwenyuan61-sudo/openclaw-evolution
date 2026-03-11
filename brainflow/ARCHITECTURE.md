# BrainFlow "活体架构"（Basal Ganglia 主线）

你选择的主线：**基底节（BG）动作选择 / 门控**。

## 核心原则（已落地）
- 脑潮（BrainFlow）只做：检索/思考/生成候选（outbox）/生成技能草案（procedural 草案）
- **价值判断 + 是否对外说话 + 是否执行高风险动作**：由亲碗（OpenClaw 主框架）统一决定

## 模块映射（工程版脑区）
- Thalamus Router：把输入/发现写入 outbox（候选流）
- Cortex/Memory：semantic/episodic/procedural 三记忆（逐步巩固）
- Cerebellum：评估器/误差校正（后续加）
- **Basal Ganglia（本主线）**：候选动作选择（在 outbox 里输出 action candidates + score），最终由亲碗采纳

## 自我升级（技能增长）
- BrainFlow 可以提出：
  - 新工作流（workflow）草案
  - 新插件（plugin）骨架 + 测试骨架
- 但不自动上线/不自动执行危险动作。
