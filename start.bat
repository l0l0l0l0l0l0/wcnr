@echo off
chcp 65001 > nul
cd /d "%~dp0"

:: 检查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 创建虚拟环境
if not exist ".venv\" (
    echo 正在创建虚拟环境...
    python -m venv .venv
)

:: 安装依赖
.venv\Scripts\python -m pip install -q --no-index --find-links deps -r requirements.txt 2> nul || .venv\Scripts\python -m pip install -q -r requirements.txt

echo 启动服务...
.venv\Scripts\python run.py
pause
