@echo off
chcp 65001 > nul
cd /d "%~dp0"

set REQUIREMENTS=%~dp0..\requirements.txt
set CACHE_DIR=%~dp0pip_cache

if not exist "%CACHE_DIR%" (
    echo 错误: 未找到 pip_cache 目录
    echo 请先在有互联网的机器上运行 download.bat 下载依赖
    pause
    exit /b 1
)

:: 检查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 创建虚拟环境
if not exist "%~dp0..\.venv\" (
    echo 正在创建虚拟环境...
    python -m venv "%~dp0..\.venv"
)

echo 正在从本地缓存安装依赖 ...
.venv\Scripts\python -m pip install --no-index --find-links="%CACHE_DIR%" -r "%REQUIREMENTS%"

if errorlevel 1 (
    echo.
    echo 安装失败，请检查 pip_cache 目录是否包含所有依赖
    pause
    exit /b 1
)

echo.
echo 安装完成！
echo 运行项目: 双击 start.bat 或执行 python run.py
pause
