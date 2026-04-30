@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo   天网可视化系统 - 内网离线部署
echo ============================================================
echo.

:: 检查 Python
python --version > nul 2>&1
if errorlevel 1 (
    echo 错误：未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: -------- 生成不含注释的 requirements --------
echo [0/3] 准备依赖清单 ...
python -c "lines=[l.strip() for l in open('requirements.txt','r',encoding='utf-8') if l.strip() and not l.strip().startswith('#')]; open('requirements_clean.txt','w',encoding='utf-8').write('\n'.join(lines))"

:: -------- 第1步：创建虚拟环境 --------
if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 正在创建虚拟环境 ...
    python -m venv .venv
    echo       虚拟环境创建完成。
) else (
    echo [1/3] 虚拟环境已存在，跳过。
)

:: -------- 第2步：升级 pip --------
echo [2/3] 正在升级 pip ...
.venv\Scripts\python -m pip install --upgrade pip --no-index --find-links=offline_deps\pip_cache 2>nul || .venv\Scripts\python -m pip install --upgrade pip 2>nul

:: -------- 第3步：离线安装依赖 --------
echo [3/3] 正在安装项目依赖 ...
.venv\Scripts\python -m pip install --no-index --find-links=offline_deps\pip_cache -r requirements_clean.txt
if errorlevel 1 (
    echo 错误：依赖安装失败，请检查 offline_deps\pip_cache 目录。
    pause
    exit /b 1
)

:: 清理临时文件
del /q requirements_clean.txt 2>nul

echo.
echo ============================================================
echo   部署完成！
echo.
echo   下一步：
echo     1. 复制 .env.example 为 .env 并修改数据库配置
echo     2. 导入 init_mysql.sql 到 MySQL
echo     3. 双击 start.bat 启动服务
echo ============================================================
pause
