@echo off
chcp 65001 >nul
cd /d "%~dp0"
set "PIP_INDEX=https://mirrors.aliyun.com/pypi/simple/"

if not exist ".venv\Scripts\python.exe" (
    echo [1/3] 正在创建虚拟环境...
    where py >nul 2>nul && (py -3 -m venv .venv) || (python -m venv .venv)
)

echo [2/3] 正在升级 pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip -i %PIP_INDEX% --progress-bar off

echo [3/3] 正在安装依赖（PySide6 / PyMuPDF / pywin32 / Pillow）...
".venv\Scripts\python.exe" -m pip install -r requirements.txt -i %PIP_INDEX% --progress-bar off

echo.
echo 安装完成。双击「启动.bat」即可运行。
pause
