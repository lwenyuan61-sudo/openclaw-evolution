创建桌面快捷方式（推荐用 .bat）：

方案A：指向 start_naochao.bat
1) 打开资源管理器，进入：C:\Users\15305\.openclaw\workspace\brainflow
2) 右键 start_naochao.bat -> 发送到 -> 桌面快捷方式
3) 以后双击桌面快捷方式即可启动脑潮

方案B：指向 start_naochao.ps1（更灵活）
1) 桌面右键 -> 新建 -> 快捷方式
2) 目标填写：
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\Users\15305\.openclaw\workspace\brainflow\start_naochao.ps1"
3) 命名为：启动脑潮

注意：OpenClaw gateway 需要单独在另一个窗口运行：
  openclaw gateway
因为你当前不是“服务安装”模式，openclaw gateway restart/stop 不生效。
