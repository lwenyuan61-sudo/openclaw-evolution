@echo off
set BASE=C:\Users\15305\.openclaw\workspace\brainflow
cd /d %BASE%

REM Launch GUI without console
start "NaoChao Launcher" /B pythonw "%BASE%\naochao_launcher.pyw"
