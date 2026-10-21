# -*- coding: utf-8 -*-
"""端到端测试：真实启动界面 -> 添加文件 -> 点击导出 -> 校验产物。

用法：
    .venv\\Scripts\\python.exe tools\\test_ui_export.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer                       # noqa: E402
from PySide6.QtGui import QFont                         # noqa: E402
from PySide6.QtWidgets import QApplication              # noqa: E402

from app.ui import theme                                # noqa: E402
from app.ui.main_window import MainWindow               # noqa: E402

OUT = ROOT / "samples" / "_ui_export"
RESULT: dict = {}


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)

    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(theme.QSS)

    window = MainWindow()
    window.resize(1360, 850)
    window.show()

    state = {"ticks": 0, "phase": "wait-parse"}

    def finish(code: int) -> None:
        window.close()
        app.quit()
        RESULT["code"] = code

    def poll() -> None:
        state["ticks"] += 1
        if state["ticks"] > 300:
            print("[FAIL] 超时", flush=True)
            finish(1)
            return

        if state["phase"] == "wait-parse":
            infos = list(window._files.values())
            if infos and all(i["state"] in ("ok", "error") for i in infos):
                print("解析完成:", [(Path(i["path"]).name, i["state"], i["pages"])
                                    for i in infos], flush=True)
                state["phase"] = "export"
                window.settings.edit_outdir.setText(str(OUT))
                window.settings.combo_page_mode.setCurrentIndex(0)   # 全部页面
                window.settings.check_subfolder.setChecked(True)
                QTimer.singleShot(200, start_export)

    def start_export() -> None:
        print("点击开始导出", flush=True)
        window.btn_start.click()
        worker = window.export_worker
        if worker is None:
            print("[FAIL] 导出未启动", flush=True)
            finish(1)
            return
        worker.finished_all.connect(on_done)
        worker.failed.connect(lambda p, m: print("  [失败]", Path(p).name, m, flush=True))

    def on_done(files: int, images: int, outdir: str) -> None:
        print(f"导出完成: {files} 文件 / {images} 张 -> {outdir}", flush=True)
        RESULT.update(files=files, images=images)
        QTimer.singleShot(300, single_page)

    def single_page() -> None:
        # 再测一次"导出此页"
        window.file_list.setCurrentRow(0)
        print("测试单页导出（第 2 页）", flush=True)
        window._goto_page(2)
        QTimer.singleShot(500, do_single)

    def do_single() -> None:
        window.settings.edit_outdir.setText(str(OUT / "single"))
        window.btn_export_this.click()
        worker = window.export_worker
        if worker is None:
            print("[FAIL] 单页导出未启动", flush=True)
            finish(1)
            return
        worker.finished_all.connect(on_single_done)

    def on_single_done(files: int, images: int, outdir: str) -> None:
        print(f"单页导出完成: {images} 张 -> {outdir}", flush=True)
        RESULT.update(single=images)
        QTimer.singleShot(200, verify)

    def verify() -> None:
        files = sorted(p.relative_to(OUT) for p in OUT.rglob("*") if p.is_file())
        print(f"产物共 {len(files)} 个：", flush=True)
        for f in files:
            print("   ", f, flush=True)
        ok = (RESULT.get("files") == 2 and RESULT.get("images") == 8
              and RESULT.get("single") == 1)
        print("端到端测试通过" if ok else "端到端测试失败", flush=True)
        finish(0 if ok else 1)

    window.add_files([
        str(ROOT / "samples" / "测试演示.pptx"),
        str(ROOT / "samples" / "测试文档.pdf"),
    ])

    timer = QTimer(window)
    timer.timeout.connect(poll)
    timer.start(400)
    window._poll_timer = timer

    app.exec()
    return int(RESULT.get("code", 1))


if __name__ == "__main__":
    sys.exit(main())
