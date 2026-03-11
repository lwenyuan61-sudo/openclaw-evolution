# BrainFlow (MVP)

这是一个“认知架构 + 可自我生成插件(workflow-in-workflow)”的最小可运行骨架。

> 重要：你说“虚拟机就是目前电脑”，这意味着没有天然隔离。
> 我强烈建议你至少使用 **WSL2/Hyper-V/Windows Sandbox/Docker** 做隔离执行域；
> 在没有隔离前，本项目默认只做 **只读/低风险动作**，并且所有“写系统/删文件/发消息”等动作都需要你手动确认。

## 目标（MVP）
- 能加载并执行 YAML 工作流（步骤可调用：工具/子工作流/插件函数）。
- 工作流内部可以触发 `SYNTHESIZE_PLUGIN` 生成一个新插件（先写 spec，再写代码），并在沙盒里跑测试。
- 通过评估后注册到 `registry/`，成为可复用“程序性记忆”。

## 目录结构
- `core/`：事件、工作流内核、调度
- `plugins/`：插件源码（每个插件一个包）
- `registry/`：已注册插件/工作流的元数据（程序性记忆）
- `workflows/`：工作流 YAML
- `runs/`：每次运行的 trace 日志

## 快速开始（建议 Python）
1) 安装 Python 3.10+。
2) 在本目录创建虚拟环境并安装依赖：

```powershell
cd C:\Users\15305\.openclaw\workspace\brainflow
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

3) 运行示例工作流：
```powershell
python run.py workflows\demo.yaml
```

## 下一步
- 你确认隔离方案（WSL2/Docker/Windows Sandbox）后，我再把“高权限执行器”接上（文件写入、进程执行、浏览器自动化等）。
