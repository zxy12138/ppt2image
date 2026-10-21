# -*- coding: utf-8 -*-
"""渲染主窗口截图，用于检查布局。

用法：
    .venv\\Scripts\\python.exe tools\\shot_ui.py [输出目录]

流程由解析完成事件驱动，避免固定 sleep 造成截图时机不准。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# 默认用真实平台（字体正确）；设 PPT2IMG_OFFSCREEN=1 可切换离屏渲染
if os.environ.get("PPT2IMG_OFFSCREEN") == "1":
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, QTimer            # noqa: E402
from PySide6.QtGui import QFont                        # noqa: E402
from PySide6.QtWidgets import QApplication             # noqa: E402

from app.ui import theme                               # noqa: E402
from app.ui.main_window import MainWindow              # noqa: E402

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "samples" / "_out"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv[:1])
    app.setStyle("Fusion")
    app.setFont(QFont("Microsoft YaHei UI", 9))
    app.setStyleSheet(theme.QSS)

    window = MainWindow()
    window.resize(1360, 850)
    window.show()

    # 每次截图都从空白配置开始，避免把上次的路径带到截图里
    window.settings.edit_outdir.clear()

    state = {"shot_done": 0, "waited": 0}

    def shot(name: str) -> None:
        path = OUT / name
        window.grab().save(str(path))
        print("saved", path, flush=True)

    def finish() -> None:
        window.close()
        app.quit()

    # 等所有文件解析完成后再截图
    def poll() -> None:
        if state["shot_done"] > 0:
            return
        state["waited"] += 1
        infos = list(window._files.values())
        ready = bool(infos) and all(i["state"] in ("ok", "error") for i in infos)
        if not ready:
            if state["waited"] > 240:          # 最多等 120 秒
                print("等待解析超时，剩余状态:",
                      [(Path(i["path"]).name, i["state"]) for i in infos], flush=True)
                finish()
            return

        if getattr(window, "_poll_timer", None):
            window._poll_timer.stop()
        state["shot_done"] = 1
        window.file_list.setCurrentRow(0)
        QTimer.singleShot(700, lambda: shot("ui_02_loaded.png"))
        QTimer.singleShot(1200, second)

    def second() -> None:
        window._goto_page(2)
        QTimer.singleShot(700, third)

    def third() -> None:
        shot("ui_03_page.png")
        window.settings.combo_page_mode.setCurrentIndex(2)
        window.settings.edit_page_spec.setText("1,3-4")
        QTimer.singleShot(300, fourth)

    def fourth() -> None:
        shot("ui_04_range.png")
        # 触发一次真实导出，截"完成"状态（输出目录用通用示例路径，避免暴露本机目录）
        window.settings.combo_page_mode.setCurrentIndex(0)
        window.settings.edit_outdir.setText("D:\\导出图片")
        window.btn_start.click()
        worker = window.export_worker
        if worker is not None:
            worker.finished_all.connect(lambda *_: QTimer.singleShot(600, fifth))
        else:
            finish()

    def fifth() -> None:
        # 截图里不露出本机路径（日志会打印引擎路径和输出目录）
        window.btn_log.setChecked(False)
        window.log_box.setVisible(False)
        QTimer.singleShot(250, lambda: (shot("ui_05_done.png"), finish()))

    def boot() -> None:
        shot("ui_01_empty.png")
        window.add_files([
            str(ROOT / "samples" / "测试演示.pptx"),
            str(ROOT / "samples" / "测试文档.pdf"),
        ])
        timer = QTimer(window)
        timer.timeout.connect(poll)
        timer.start(500)
        window._poll_timer = timer

    QTimer.singleShot(1000, boot)
    app.exec()
    print("done", flush=True)


if __name__ == "__main__":
    main()
