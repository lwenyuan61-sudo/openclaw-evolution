# Signal Bus

目标：把现实世界与本地环境的变化统一成可积累、可路由、可学习的信号，而不是零散工具调用。

## Current signal sources

- screen-state：桌面当前状态与变化
- device-state：摄像头、麦克风、扬声器、voice 列表
- workspace changes：工作区文件变化
- future camera/audio events：未来可继续接入

## Flow

1. resident loop 或显式检查触发 signal probe
2. signal probe 先过滤自写状态噪声，再收集本地现实信号
3. 把最新一轮结果写入 `core/perception-state.json` 的 `lastProbeSignals`
4. 用 `core/event-routing.md` 判断这些信号是忽略、记录、延迟还是升级
5. 程序化习惯层优先消费低风险重复场景；只有不够时，统计学习层再参与排序
6. 统计学习层记录哪些信号真正有价值

## Rule

- signal bus 先做低成本检测，再决定要不要做更重的感知
- 不是每次检测到变化都要打扰 Lee
- resident/self 写回产生的文件变化，不应反复被当成外部世界的新信号
- 现实接入的关键不是“看见一切”，而是“把值得注意的现实变化接进当前主线”
