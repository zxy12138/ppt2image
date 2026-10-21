# -*- coding: utf-8 -*-
"""探测 WPS / PowerPoint 的 COM 接口可用性与正确调用方式。"""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SRC = ROOT / "samples" / "测试演示.pptx"
OUT = ROOT / "samples" / "_probe"

PROGIDS = ["KWPP.Application", "PowerPoint.Application", "WPP.Application",
           "Kingsoft.Presentation", "WPS.Application"]


def try_open(progid: str) -> None:
    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    print(f"\n=== {progid} ===")
    try:
        app = win32.DispatchEx(progid)
    except Exception:
        try:
            app = win32.Dispatch(progid)
        except Exception as exc:
            print(f"  Dispatch 失败: {exc}")
            return

    for attr in ("Name", "Version", "Path", "Visible"):
        try:
            print(f"  {attr} = {getattr(app, attr)}")
        except Exception as exc:
            print(f"  {attr} 读取失败: {exc}")

    try:
        print(f"  Presentations 类型: {type(app.Presentations)}")
        print(f"  Presentations.Count = {app.Presentations.Count}")
    except Exception as exc:
        print(f"  Presentations 不可用: {exc}")

    for attr, value in (("Visible", True), ("DisplayAlerts", 1),
                        ("AutomationSecurity", 1), ("WindowState", 1)):
        try:
            setattr(app, attr, value)
            print(f"  set {attr}={value} OK")
        except Exception as exc:
            print(f"  set {attr} 失败: {exc}")

    attempts = [
        ("Open(path)", lambda: app.Presentations.Open(str(SRC))),
        ("Open(path,0,0,0)", lambda: app.Presentations.Open(str(SRC), 0, 0, 0)),
        ("Open(path,-1,0,-1)", lambda: app.Presentations.Open(str(SRC), -1, 0, -1)),
        ("Open(FileName=path)", lambda: app.Presentations.Open(FileName=str(SRC))),
        ("Open2007", lambda: app.Presentations.Open2007(str(SRC), 0, 0, 0, 0)),
    ]
    pres = None
    for label, fn in attempts:
        try:
            pres = fn()
            print(f"  [成功] {label} -> 幻灯片数 {pres.Slides.Count}")
            break
        except Exception as exc:
            print(f"  [失败] {label}: {exc}")

    if pres is not None:
        OUT.mkdir(parents=True, exist_ok=True)
        dst = OUT / f"probe_{progid.split('.')[0]}.pdf"
        try:
            pres.SaveAs(str(dst), 32)
            print(f"  SaveAs PDF -> {dst.exists()} {dst.stat().st_size if dst.exists() else 0} bytes")
        except Exception as exc:
            print(f"  SaveAs PDF 失败: {exc}")
            # 试导出图片
            try:
                imgdir = OUT / "png"
                imgdir.mkdir(exist_ok=True)
                pres.Slides(1).Export(str(imgdir / "s1.png"), "PNG", 1920, 1080)
                print(f"  Slide.Export -> {(imgdir / 's1.png').exists()}")
            except Exception as exc2:
                print(f"  Slide.Export 失败: {exc2}")
            # 试 SaveCopyAs
            try:
                dst2 = OUT / f"copy_{progid.split('.')[0]}.pdf"
                pres.SaveCopyAs(str(dst2), 32)
                print(f"  SaveCopyAs -> {dst2.exists()}")
            except Exception as exc3:
                print(f"  SaveCopyAs 失败: {exc3}")
        try:
            pres.Close()
        except Exception:
            pass

    try:
        app.Quit()
    except Exception:
        pass


if __name__ == "__main__":
    for p in PROGIDS:
        try:
            try_open(p)
        except Exception:
            traceback.print_exc()
