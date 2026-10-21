# -*- coding: utf-8 -*-
"""幻灯片转图片 · 程序入口。

用法：
    .venv\\Scripts\\python.exe main.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# 打包成窗口程序后没有控制台，stdout/stderr 为 None，
# 任何 print / traceback 都会炸，这里先兜住。
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

from PySide6.QtCore import Qt                       # noqa: E402
from PySide6.QtGui import QFont                     # noqa: E402
from PySide6.QtWidgets import QApplication          # noqa: E402

from app.ui import theme                            # noqa: E402
from app.ui.main_window import MainWindow, app_icon  # noqa: E402


def run_selftest() -> int:
    """打包后自检：验证 PyMuPDF / Pillow 在 exe 环境里是否可用。

    结果写到 %TEMP%\\ppt2image_selftest.txt（窗口程序没有 stdout）。
    """
    import tempfile
    import traceback

    out = Path(tempfile.gettempdir()) / "ppt2image_selftest.txt"
    lines: list[str] = []
    status = "PASS"
    try:
        try:
            import pymupdf as fitz
        except ImportError:
            import fitz
        doc = fitz.open()
        page = doc.new_page(width=400, height=300)
        page.insert_text((40, 100), "selftest 中文 ABC", fontsize=18)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        lines.append(f"PyMuPDF OK  {pix.width}x{pix.height}px")

        import io

        from PIL import Image
        img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        lines.append(f"Pillow  OK  {img.size} {img.mode}")
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        lines.append(f"PNG 编码 OK  {len(buf.getvalue())} bytes")
        doc.close()

        import app.engines as engines
        names = [e.label for e in engines.available_engines()]
        lines.append("可用引擎：" + (", ".join(names) if names else "无"))
    except Exception:
        status = "FAIL"
        lines.append(traceback.format_exc())

    try:
        out.write_text(status + "\n" + "\n".join(lines), encoding="utf-8")
    except OSError:
        pass
    return 0 if status == "PASS" else 1


def main() -> int:
    # 打包成 exe 后，转换子进程复用同一个 exe（见 app/engines.py）
    if len(sys.argv) > 1 and sys.argv[1] == "--office-worker":
        from app.office_worker import main as worker_main
        return worker_main()

    if "--selftest" in sys.argv:
        return run_selftest()

    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv)
    app.setApplicationName("幻灯片转图片")
    app.setApplicationDisplayName("幻灯片转图片")
    app.setOrganizationName("PPT2Image")
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setWindowIcon(app_icon())
    app.setStyleSheet(theme.QSS)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
