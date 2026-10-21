@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 带控制台的启动方式，报错信息可以直接看到
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到运行环境 .venv
    echo 请先运行「安装依赖.bat」
    pause
    exit /b 1
)

".venv\Scripts\python.exe" "main.py"
echo.
echo 程序已退出。
pause
