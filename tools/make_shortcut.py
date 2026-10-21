# -*- coding: utf-8 -*-
"""在桌面创建程序快捷方式。

用法：
    .venv\\Scripts\\python.exe tools\\make_shortcut.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    import pythoncom
    from win32com.client import Dispatch

    target = Path(os.environ["LOCALAPPDATA"]) / "PPT2Image" / "app" / "幻灯片转图片.exe"
    if not target.exists():
        print("找不到程序：", target)
        return 1

    desktop = Path(os.environ["USERPROFILE"]) / "Desktop"
    lnk = desktop / "幻灯片转图片.lnk"
    if lnk.exists():
        try:
            lnk.unlink()
        except OSError as exc:
            print("无法覆盖旧快捷方式：", exc)
            return 1

    pythoncom.CoInitialize()
    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(lnk))
        shortcut.Targetpath = str(target)
        shortcut.WorkingDirectory = str(target.parent)
        shortcut.IconLocation = f"{target},0"
        shortcut.Description = "把 PPT / PPTX / PDF 的每一页导出为图片"
        shortcut.save()
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass

    print("快捷方式已创建：", lnk, "存在:", lnk.exists())
    return 0 if lnk.exists() else 1


if __name__ == "__main__":
    sys.exit(main())
