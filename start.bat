@echo off
chcp 65001 > nul
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo 错误：未找到虚拟环境，请先运行 deploy.bat
    pause
    exit /b 1
)

echo 启动服务 ...
.venv\Scripts\python run.py
pause
