@echo off
chcp 65001 > nul
cd /d "%~dp0"

set REQUIREMENTS=%~dp0..\requirements.txt
set CACHE_DIR=%~dp0pip_cache

echo 正在下载依赖到 %CACHE_DIR% ...
if not exist "%CACHE_DIR%" mkdir "%CACHE_DIR%"

:: 下载当前平台（Windows）的依赖
pip download -r "%REQUIREMENTS%" -d "%CACHE_DIR%"

:: 下载 Linux x86_64 的编译依赖
pip download -r "%REQUIREMENTS%" -d "%CACHE_DIR%" --platform manylinux2014_x86_64 --python-version 312 --only-binary=:all:

echo.
echo 下载完成！文件保存在: %CACHE_DIR%
dir /b "%CACHE_DIR%" | find /c /v "" > _tmp && set /p COUNT=<_tmp && del _tmp
echo 共 %COUNT% 个文件
echo.
echo 将 offline_deps\ 整个目录拷贝到内网机器，然后运行 install.bat
pause
