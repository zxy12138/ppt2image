@echo off
chcp 65001 >nul
cd /d "%~dp0"

rem 优先启动已部署好的 exe（启动快、无黑窗口）
set "APP=%LOCALAPPDATA%\PPT2Image\app\幻灯片转图片.exe"
if exist "%APP%" (
    start "" "%APP%"
    exit /b 0
)

rem 没部署过就用项目里的虚拟环境跑源码
if not exist ".venv\Scripts\pythonw.exe" (
    echo [错误] 未找到运行环境 .venv，也没有已安装的程序
    echo 请运行「安装依赖.bat」，或双击桌面的「幻灯片转图片」图标
    pause
    exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "main.py"
