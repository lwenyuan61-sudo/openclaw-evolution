# Continuity Scoring

用于评估连续性层是否真正让代理跨轮次保持 focus。

## Positive signal

出现以下情况时，可认为 continuity 有效：
- 连续两轮或以上 wake 延续同一 focus
- 当前动作明显来自上一轮写下的 stop point / next step
- 没有为了“显得主动”而切换到无关新主题

## Negative signal

出现以下情况时，应视为 continuity 失效或偏弱：
- 明明有未完成 focus，却重新发明新目标
- 每轮都重复宏观规划，没有沿着 stop point 前进
- 因为轻微新奇感而频繁切换轨道

## Suggested response

- Positive: 在 daily memory 记录一次有效延续；必要时提高相关 skill score 或降低切换冲动
- Negative: 在 corrections.md 写明漂移原因，并收紧 resume-loop 的切换条件
