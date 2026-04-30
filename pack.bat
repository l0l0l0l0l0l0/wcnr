@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo ============================================================
echo   天网可视化系统 - 打包部署文件
echo ============================================================
echo.

:: 1. 确保 pip_cache 存在
if not exist "offline_deps\pip_cache" (
    echo 错误：未找到 offline_deps\pip_cache，请先运行 offline_deps\download.bat
    pause
    exit /b 1
)

:: 2. 生成干净的 requirements（去除中文注释避免编码问题）
echo [1/3] 生成 requirements_clean.txt ...
python -c "lines=[l.strip() for l in open('requirements.txt','r',encoding='utf-8') if l.strip() and not l.strip().startswith('#')]; open('offline_deps/requirements_clean.txt','w',encoding='utf-8').write('\n'.join(lines))"

:: 3. 设置输出目录
set OUTPUT_DIR=%~dp0dist\wcnr_deploy
if exist "%OUTPUT_DIR%" rmdir /s /q "%OUTPUT_DIR%"
mkdir "%OUTPUT_DIR%"

:: 4. 复制项目文件（排除不需要的目录）
echo [2/3] 复制项目文件 ...

:: 复制 Python 源码
xcopy /e /i /q "app" "%OUTPUT_DIR%\app" > nul
xcopy /e /i /q "models" "%OUTPUT_DIR%\models" > nul
xcopy /e /i /q "routers" "%OUTPUT_DIR%\routers" > nul
xcopy /e /i /q "services" "%OUTPUT_DIR%\services" > nul
xcopy /e /i /q "scheduler" "%OUTPUT_DIR%\scheduler" > nul
xcopy /e /i /q "dify_modules" "%OUTPUT_DIR%\dify_modules" > nul
xcopy /e /i /q "static" "%OUTPUT_DIR%\static" > nul
xcopy /e /i /q "templates" "%OUTPUT_DIR%\templates" > nul

:: 复制 offline_deps
xcopy /e /i /q "offline_deps" "%OUTPUT_DIR%\offline_deps" > nul

:: 复制根目录文件
copy /y "run.py" "%OUTPUT_DIR%\" > nul
copy /y "config.py" "%OUTPUT_DIR%\" > nul
copy /y "requirements.txt" "%OUTPUT_DIR%\" > nul
copy /y ".env.example" "%OUTPUT_DIR%\" > nul
copy /y "init_mysql.sql" "%OUTPUT_DIR%\" > nul
copy /y "deploy.bat" "%OUTPUT_DIR%\" > nul
copy /y "start.bat" "%OUTPUT_DIR%\" > nul

:: 复制 .env（如果存在）
if exist ".env" copy /y ".env" "%OUTPUT_DIR%\" > nul

:: 5. 清理 __pycache__
echo [3/3] 清理缓存文件 ...
for /d /r "%OUTPUT_DIR%" %%d in (__pycache__) do (
    if exist "%%d" rmdir /s /q "%%d"
)

:: 6. 打包为 ZIP
echo.
echo 正在压缩为 ZIP ...
set ZIP_NAME=wcnr_deploy_%date:~0,4%%date:~5,2%%date:~8,2%.zip
set ZIP_PATH=%~dp0dist\%ZIP_NAME%

if exist "%ZIP_PATH%" del /q "%ZIP_PATH%"

:: 使用 PowerShell 压缩
powershell -Command "Compress-Archive -Path '%OUTPUT_DIR%\*' -DestinationPath '%ZIP_PATH%' -Force"

if errorlevel 1 (
    echo 错误：压缩失败
    pause
    exit /b 1
)

:: 清理临时目录
rmdir /s /q "%OUTPUT_DIR%"

echo.
echo ============================================================
echo   打包完成！
echo.
echo   部署包: %ZIP_PATH%
echo.
echo   部署步骤：
echo     1. 将 ZIP 拷贝到内网服务器并解压
echo     2. 双击 deploy.bat 安装依赖
echo     3. 复制 .env.example 为 .env 并修改配置
echo     4. 导入 init_mysql.sql 到 MySQL
echo     5. 双击 start.bat 启动服务
echo ============================================================
pause
