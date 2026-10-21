# -*- coding: utf-8 -*-
"""独立的 Office 转换子进程。

由主程序调用：
    python office_worker.py <ProgID> <源文件> <目标PDF>

为什么放在子进程里
------------------
* COM 调用一旦卡死（Office 弹窗、无响应），父进程可以直接超时 kill，
  不会把整个界面拖死；
* 进程退出后 Office 实例随之清理，不会在任务栏残留；
* Office 崩溃 / 崩溃弹窗与主程序隔离。

退出码：0 成功，2 创建实例失败，3 打开失败，4 保存失败，5 输出为空
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

_PP_SAVE_AS_PDF = 32

# 打包成窗口程序（无控制台）后 sys.stderr 是 None，
# 错误信息改为写同目录的 .err 文件，由父进程读取。
_ERR_PATH: Path | None = None


def _fail(code: int, message: str) -> int:
    message = message.strip()[:600]
    try:
        sys.stderr.write(message)
    except Exception:
        pass
    if _ERR_PATH is not None:
        try:
            _ERR_PATH.write_text(message, encoding="utf-8")
        except Exception:
            pass
    return code


def convert(progid: str, src: Path, dst: Path) -> int:
    import pythoncom
    import win32com.client as win32

    pythoncom.CoInitialize()
    app = None
    pres = None
    try:
        try:
            app = win32.DispatchEx(progid)
        except Exception as exc:
            try:
                app = win32.Dispatch(progid)
            except Exception:
                return _fail(2, f"无法启动 {progid}：{exc}")

        # WPS 只有在 Visible=True 时才能自动化，随后最小化到任务栏
        for attr, value in (("Visible", True), ("DisplayAlerts", 1),
                            ("WindowState", 1), ("AutomationSecurity", 1)):
            try:
                setattr(app, attr, value)
            except Exception:
                pass

        try:
            pres = app.Presentations.Open(str(src))
        except Exception as exc:
            return _fail(3, f"{src.name} 打开失败：文件可能已损坏、被加密，"
                            f"或该格式不被 {progid.split('.')[0]} 支持（{exc}）")

        if pres is None:
            return _fail(3, f"{src.name} 打开失败：未返回演示文稿对象")

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                dst.unlink()
        except OSError:
            pass

        try:
            pres.SaveAs(str(dst), _PP_SAVE_AS_PDF)
        except Exception as exc:
            return _fail(4, f"{src.name} 导出 PDF 失败：{exc}")

        for _ in range(150):
            if dst.exists() and dst.stat().st_size > 0:
                break
            time.sleep(0.1)

        if not dst.exists() or dst.stat().st_size == 0:
            return _fail(5, f"{src.name} 未能生成 PDF（可能被阅读器占用或格式特殊）")
        return 0
    finally:
        if pres is not None:
            try:
                pres.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def main(argv: list[str] | None = None) -> int:
    """入口。打包后由 main.py 以 `exe --office-worker ...` 方式调用。"""
    global _ERR_PATH
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "--office-worker":
        args = args[1:]
    if len(args) < 3:
        return _fail(1, "用法：office_worker.py <ProgID> <源文件> <目标PDF>")

    progid, src, dst = args[0], Path(args[1]), Path(args[2])
    try:
        src = src.resolve()
        dst = dst.resolve()
        _ERR_PATH = dst.with_suffix(dst.suffix + ".err")
        return convert(progid, src, dst)
    except Exception as exc:  # pragma: no cover
        return _fail(9, f"转换异常：{exc}")


if __name__ == "__main__":
    sys.exit(main())
