# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：单文件、无控制台窗口。

打包命令：
    .venv\\Scripts\\pyinstaller.exe build.spec --noconfirm --clean

产物：
    dist\\幻灯片转图片.exe
"""

from pathlib import Path

ROOT = Path(SPECPATH)

# 用不到的 Qt / 科学计算模块一律排除，明显压缩体积
EXCLUDES = [
    # Qt 大型可选组件
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtWebChannel",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DCore", "PySide6.Qt3DExtras",
    "PySide6.Qt3DInput", "PySide6.Qt3DLogic", "PySide6.Qt3DRender",
    "PySide6.QtCharts", "PySide6.QtDataVisualization", "PySide6.QtGraphs",
    "PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets",
    "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtQuick3D",
    "PySide6.QtQuickWidgets", "PySide6.QtQuickControls2",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtBluetooth",
    "PySide6.QtNfc", "PySide6.QtPositioning", "PySide6.QtLocation",
    "PySide6.QtSerialPort", "PySide6.QtWebSockets", "PySide6.QtWebSocketsQuick",
    "PySide6.QtRemoteObjects", "PySide6.QtScxml", "PySide6.QtSensors",
    "PySide6.QtSpatialAudio", "PySide6.QtStateMachine", "PySide6.QtTextToSpeech",
    "PySide6.QtUiTools", "PySide6.QtHelp", "PySide6.QtDesigner",
    "PySide6.QtHttpServer", "PySide6.QtNetworkAuth", "PySide6.QtGraphsWidgets",
    # 与本工具无关的第三方库
    "matplotlib", "numpy", "scipy", "pandas",
    "pptx", "lxml", "PyQt5", "PyQt6", "PySide2",
    "pytest", "unittest", "pydoc", "doctest",
]

a = Analysis(
    [str(ROOT / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "win32com.client", "pythoncom", "pywintypes", "win32com.client.dynamic",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=0,
)

# 剔除运行时确认用不到的大文件（与 build_onedir.spec 保持一致）
_DROP_FILES = {
    "opengl32sw.dll", "qt6quick.dll", "qt6qml.dll", "qt6qmlmodels.dll",
    "qt6pdf.dll", "qt6pdfwidgets.dll",
}


def _is_dropped(path: str) -> bool:
    name = str(path).lower().replace("\\", "/").rsplit("/", 1)[-1]
    if name in _DROP_FILES:
        return True
    return name.startswith("_avif.") or name.startswith("_imagingcms.")


a.binaries = [b for b in a.binaries if not _is_dropped(b[0])]
a.datas = [d for d in a.datas if not _is_dropped(d[0])]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="幻灯片转图片",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "app.ico"),
)
