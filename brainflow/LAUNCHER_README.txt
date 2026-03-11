桌面快捷方式（带3个按钮的启动器）

文件：
- naochao_launcher.bat   （推荐，双击即可）
- naochao_launcher.pyw   （GUI 程序）

创建桌面快捷方式：
1) 打开：C:\Users\15305\.openclaw\workspace\brainflow
2) 右键 naochao_launcher.bat -> 发送到 -> 桌面快捷方式
3) 双击桌面快捷方式即可打开带按钮的界面

按钮说明：
- 启动 OpenClaw 网关：相当于运行 openclaw gateway（会弹出新窗口）
- 打开 Dashboard：打开 http://127.0.0.1:18789/
- 启动 脑潮：运行 start_naochao.bat（会弹出新窗口并持续运行）

图片说明：
- 启动器会读取 brainflow\girl_ui.png 作为装饰图（128x128，适配窗口，不遮挡按钮）。
- 原图保存为 brainflow\girl_raw.jpg。
- 如需换图：修改 prepare_avatar.py 里的 IMAGE_URL 后重新运行。
