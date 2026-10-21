# -*- coding: utf-8 -*-
"""主窗口：文件列表 + 逐页预览 + 参数面板 + 导出进度。"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer, QUrl
from PySide6.QtGui import (QAction, QColor, QDesktopServices, QIcon, QPainter,
                           QPen, QPixmap)
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QFrame, QHBoxLayout,
                               QLabel, QMainWindow, QMenu, QMessageBox,
                               QPlainTextEdit, QProgressBar, QPushButton,
                               QSpinBox, QSplitter, QVBoxLayout, QWidget)

from ..converter import DocumentLoader
from ..engines import SUPPORTED_EXTS, Engine, detect_engines
from ..pages import validate_page_spec
from ..worker import ExportWorker, FileTask, ParseWorker
from . import theme
from .settings_panel import SettingsPanel
from .widgets import (ROLE_PAGES, ROLE_STATE, ROLE_STATUS, Card, FileList,
                      PreviewView)


def app_icon(size: int = 64) -> QIcon:
    """用代码画一个应用图标，避免依赖外部资源。"""
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(theme.PRIMARY))
    p.drawRoundedRect(QRectF(3, 3, size - 6, size - 6), size * 0.24, size * 0.24)

    p.setBrush(QColor("#FFFFFF"))
    p.drawRoundedRect(QRectF(size * 0.26, size * 0.24, size * 0.48, size * 0.36),
                      size * 0.05, size * 0.05)
    p.setPen(QPen(QColor(theme.PRIMARY), size * 0.055, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(int(size * 0.36), int(size * 0.70), int(size * 0.64), int(size * 0.70))
    p.drawLine(int(size * 0.36), int(size * 0.80), int(size * 0.56), int(size * 0.80))
    p.end()
    return QIcon(pm)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("幻灯片转图片 · 逐页导出工具")
        self.setWindowIcon(app_icon())
        self.resize(1300, 840)
        self.setMinimumSize(1040, 700)
        self.setAcceptDrops(True)

        # ---- 状态 ----
        self._files: dict[str, dict] = {}
        self._engines: list[Engine] = []
        self._engine: Engine | None = None
        self._current_path: str | None = None
        self._current_page = 1
        self._pix_cache: dict[tuple[str, int], QPixmap] = {}
        self._exporting = False
        self._last_outdir = ""

        cache_root = Path.home() / "AppData" / "Local" / "PPT2Image" / "cache"
        self._loader = DocumentLoader(cache_root)

        self._build_ui()
        self._build_workers()
        QTimer.singleShot(60, self._detect_engines)

    # ------------------------------------------------------------------ #
    # 界面
    # ------------------------------------------------------------------ #
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_header())
        layout.addWidget(self._build_body(), 1)
        layout.addWidget(self._build_log())
        layout.addWidget(self._build_footer())

    # -- 顶部 ------------------------------------------------------------- #
    def _build_header(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Header")
        frame.setFixedHeight(66)

        row = QHBoxLayout(frame)
        row.setContentsMargins(20, 10, 20, 10)
        row.setSpacing(12)

        icon = QLabel()
        icon.setPixmap(app_icon(36).pixmap(36, 36))
        icon.setFixedSize(36, 36)
        row.addWidget(icon)

        title_box = QVBoxLayout()
        title_box.setSpacing(1)
        title = QLabel("幻灯片转图片")
        title.setObjectName("AppTitle")
        subtitle = QLabel("把 PPT / PPTX / PDF 的每一页导出为高清图片")
        subtitle.setObjectName("AppSubtitle")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        row.addLayout(title_box)
        row.addStretch(1)

        self.chip_engine = QPushButton("正在检测转换引擎…")
        self.chip_engine.setObjectName("EngineChip")
        self.chip_engine.setCursor(Qt.PointingHandCursor)
        self.chip_engine.clicked.connect(self._show_engine_menu)
        row.addWidget(self.chip_engine)
        return frame

    # -- 主体 ------------------------------------------------------------- #
    def _build_body(self) -> QWidget:
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(2)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_center())
        splitter.addWidget(self._build_right())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)
        splitter.setSizes([340, 620, 350])
        return splitter

    def _build_left(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(16, 12, 4, 12)
        layout.setSpacing(10)

        card = Card("文件列表")
        body = card.body()

        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        self.check_all = QCheckBox("全选")
        self.check_all.setChecked(True)
        self.check_all.stateChanged.connect(self._toggle_all)
        self.label_count = QLabel("0 个文件")
        self.label_count.setObjectName("CardHint")
        top_row.addWidget(self.check_all)
        top_row.addStretch(1)
        top_row.addWidget(self.label_count)
        body.addLayout(top_row)

        self.file_list = FileList()
        self.file_list.itemSelectionChanged.connect(self._on_selection_changed)
        body.addWidget(self.file_list, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)
        self.btn_add = QPushButton("＋ 添加文件")
        self.btn_add.clicked.connect(self._pick_files)
        self.btn_remove = QPushButton("移除")
        self.btn_remove.clicked.connect(self._remove_selected)
        self.btn_clear = QPushButton("清空")
        self.btn_clear.clicked.connect(self._clear_files)
        btn_row.addWidget(self.btn_add, 2)
        btn_row.addWidget(self.btn_remove, 1)
        btn_row.addWidget(self.btn_clear, 1)
        body.addLayout(btn_row)

        layout.addWidget(card, 1)
        return wrap

    def _build_center(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(6, 12, 6, 12)
        layout.setSpacing(10)

        card = Card()
        body = card.body()

        head = QHBoxLayout()
        head.setSpacing(8)
        self.preview_title = QLabel("未选择文件")
        self.preview_title.setObjectName("CardTitle")
        self.preview_title.setMinimumWidth(80)
        self.label_page_badge = QLabel("")
        self.label_page_badge.setObjectName("CardHint")
        head.addWidget(self.preview_title, 1)
        head.addWidget(self.label_page_badge)
        body.addLayout(head)

        self.preview = PreviewView()
        self.preview.setText("添加文件后，在这里预览每一页")
        self.preview.setStyleSheet(
            f"#PreviewStage {{ background:{theme.BG}; border-radius:10px; color:{theme.TEXT_FAINT}; }}")
        body.addWidget(self.preview, 1)

        nav = QHBoxLayout()
        nav.setSpacing(8)
        self.btn_prev = QPushButton("‹")
        self.btn_prev.setObjectName("IconButton")
        self.btn_prev.setFixedWidth(34)
        self.btn_prev.clicked.connect(lambda: self._step_page(-1))
        self.btn_next = QPushButton("›")
        self.btn_next.setObjectName("IconButton")
        self.btn_next.setFixedWidth(34)
        self.btn_next.clicked.connect(lambda: self._step_page(1))

        self.spin_page = QSpinBox()
        self.spin_page.setRange(1, 1)
        self.spin_page.setFixedWidth(72)
        self.spin_page.setAlignment(Qt.AlignCenter)
        self.spin_page.valueChanged.connect(self._on_page_spin)

        self.label_total = QLabel("/ 0")
        self.label_total.setObjectName("CardHint")

        self.btn_export_this = QPushButton("导出此页")
        self.btn_export_this.clicked.connect(lambda: self._start_export(only_current=True))
        self.btn_export_this.setEnabled(False)

        nav.addWidget(self.btn_prev)
        nav.addWidget(self.spin_page)
        nav.addWidget(self.label_total)
        nav.addWidget(self.btn_next)
        nav.addStretch(1)
        nav.addWidget(self.btn_export_this)
        body.addLayout(nav)

        layout.addWidget(card, 1)
        return wrap

    def _build_right(self) -> QWidget:
        wrap = QWidget()
        layout = QVBoxLayout(wrap)
        layout.setContentsMargins(4, 12, 12, 12)
        layout.setSpacing(0)

        self.settings = SettingsPanel()
        self.settings.changed.connect(self._refresh_estimate)
        layout.addWidget(self.settings)
        return wrap

    # -- 日志 ------------------------------------------------------------- #
    def _build_log(self) -> QWidget:
        self.log_box = QPlainTextEdit()
        self.log_box.setObjectName("Log")
        self.log_box.setReadOnly(True)
        self.log_box.setFixedHeight(132)
        self.log_box.setMaximumBlockCount(800)
        self.log_box.setVisible(False)
        return self.log_box

    # -- 底部 ------------------------------------------------------------- #
    def _build_footer(self) -> QWidget:
        frame = QFrame()
        frame.setObjectName("Footer")
        frame.setStyleSheet(
            f"#Footer {{ background:{theme.SURFACE}; border-top:1px solid {theme.BORDER}; }}")
        frame.setFixedHeight(76)

        row = QHBoxLayout(frame)
        row.setContentsMargins(20, 12, 20, 12)
        row.setSpacing(14)

        left = QVBoxLayout()
        left.setSpacing(7)
        self.label_status = QLabel("就绪 · 添加文件后开始")
        self.label_status.setObjectName("CardHint")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        left.addWidget(self.label_status)
        left.addWidget(self.progress)
        row.addLayout(left, 1)

        self.btn_log = QPushButton("任务日志")
        self.btn_log.setObjectName("Ghost")
        self.btn_log.setCheckable(True)
        self.btn_log.toggled.connect(self._toggle_log)
        row.addWidget(self.btn_log)

        self.btn_open = QPushButton("打开输出目录")
        self.btn_open.setEnabled(False)
        self.btn_open.clicked.connect(self._open_outdir)
        row.addWidget(self.btn_open)

        self.btn_cancel = QPushButton("取消")
        self.btn_cancel.setVisible(False)
        self.btn_cancel.clicked.connect(self._cancel_export)
        row.addWidget(self.btn_cancel)

        self.btn_start = QPushButton("开始导出")
        self.btn_start.setObjectName("Primary")
        self.btn_start.setMinimumWidth(120)
        self.btn_start.clicked.connect(lambda: self._start_export(False))
        row.addWidget(self.btn_start)
        return frame

    # ------------------------------------------------------------------ #
    # 引擎
    # ------------------------------------------------------------------ #
    def _detect_engines(self) -> None:
        self._engines = detect_engines()
        usable = [e for e in self._engines if e.available]
        self._engine = usable[0] if usable else None

        if self._engine:
            self.chip_engine.setText(f"引擎 · {self._engine.label}")
            self.chip_engine.setProperty("state", "ok")
            self._log(f"转换引擎：{self._engine.label}（{self._engine.detail}）")
        else:
            self.chip_engine.setText("未检测到转换引擎")
            self.chip_engine.setProperty("state", "error")
            self._log("未检测到 PowerPoint / WPS / LibreOffice，PPT 类文件无法转换（PDF 不受影响）")

        self._restyle(self.chip_engine)
        self._build_engine_actions()

        if self.parse_worker:
            self.parse_worker.set_engine(self._engine)

        # 引擎就绪后，把之前因缺引擎失败的 PPT 重新排队
        for path, info in self._files.items():
            if info.get("state") == "error":
                self._requeue_parse(path, info)

    def _build_engine_actions(self) -> None:
        self._engine_menu = QMenu(self)
        for engine in self._engines:
            text = engine.label + ("" if engine.available else "（不可用）")
            action = QAction(text, self)
            action.setCheckable(True)
            action.setChecked(engine is self._engine)
            action.setEnabled(engine.available)
            action.setToolTip(engine.detail)
            action.triggered.connect(lambda _=False, e=engine: self._switch_engine(e))
            self._engine_menu.addAction(action)
        self._engine_menu.addSeparator()
        refresh = QAction("重新检测", self)
        refresh.triggered.connect(self._detect_engines)
        self._engine_menu.addAction(refresh)

    def _show_engine_menu(self) -> None:
        if not hasattr(self, "_engine_menu"):
            return
        self._build_engine_actions()
        self._engine_menu.exec(self.chip_engine.mapToGlobal(
            self.chip_engine.rect().bottomLeft()))

    def _switch_engine(self, engine: Engine) -> None:
        self._engine = engine
        self.chip_engine.setText(f"引擎 · {engine.label}")
        self.chip_engine.setProperty("state", "ok")
        self._restyle(self.chip_engine)
        if self.parse_worker:
            self.parse_worker.set_engine(engine)
        self._log(f"已切换转换引擎：{engine.label}")

    @staticmethod
    def _restyle(widget: QWidget) -> None:
        widget.style().unpolish(widget)
        widget.style().polish(widget)

    # ------------------------------------------------------------------ #
    # 线程
    # ------------------------------------------------------------------ #
    def _build_workers(self) -> None:
        self.parse_worker = ParseWorker(self._loader, self._loader.workdir, self)
        self.parse_worker.parsed.connect(self._on_parsed)
        self.parse_worker.failed.connect(self._on_parse_failed)
        self.parse_worker.preview_ready.connect(self._on_preview_ready)
        self.parse_worker.start()
        self.export_worker: ExportWorker | None = None

    # ------------------------------------------------------------------ #
    # 文件操作
    # ------------------------------------------------------------------ #
    def _pick_files(self) -> None:
        patterns = " ".join(f"*{ext}" for ext in sorted(SUPPORTED_EXTS))
        paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要转换的文件", "",
            f"支持的文件 ({patterns});;演示文稿 (*.ppt *.pptx *.pptm *.pps *.ppsx);;PDF (*.pdf);;所有文件 (*.*)")
        if paths:
            self.add_files(paths)

    def add_files(self, paths: list[str]) -> None:
        added = 0
        skipped: list[str] = []
        for raw in paths:
            path = Path(raw)
            if not path.is_file():
                continue
            if path.suffix.lower() not in SUPPORTED_EXTS:
                skipped.append(path.name)
                continue
            key = str(path.resolve())
            if key in self._files:
                continue

            info = {
                "path": path,
                "pages": 0,
                "w": 0,
                "h": 0,
                "state": "pending",
                "item": None,
            }
            kind = path.suffix.lstrip(".").upper()
            item = self.file_list.add_file(str(path).replace("\\", "/"), kind)
            info["item"] = item
            self._files[key] = info
            self.parse_worker.request_parse(path)
            added += 1

        if skipped:
            self._log(f"已忽略 {len(skipped)} 个不支持的文件：{', '.join(skipped[:5])}"
                      + (" 等" if len(skipped) > 5 else ""))
        if added:
            self._log(f"已添加 {added} 个文件，正在解析…")
            self._update_counts()
            if self.file_list.currentRow() < 0 and self.file_list.count() > 0:
                self.file_list.setCurrentRow(0)

    def _remove_selected(self) -> None:
        items = self.file_list.selectedItems()
        if not items:
            return
        for item in items:
            key = str(Path(item.data(Qt.UserRole)).resolve())
            self._files.pop(key, None)
            self.file_list.takeItem(self.file_list.row(item))
        self._update_counts()
        self._on_selection_changed()

    def _clear_files(self) -> None:
        self.file_list.clear()
        self._files.clear()
        self._pix_cache.clear()
        self.preview.show_message("添加文件后，在这里预览每一页")
        self.preview_title.setText("未选择文件")
        self.label_page_badge.setText("")
        self.label_total.setText("/ 0")
        self.spin_page.setRange(1, 1)
        self.btn_export_this.setEnabled(False)
        self._update_counts()

    def _toggle_all(self, state: int) -> None:
        checked = Qt.Checked if state == Qt.Checked else Qt.Unchecked
        for info in self._files.values():
            info["item"].setCheckState(checked)
        self._update_counts()

    def _update_counts(self) -> None:
        total = len(self._files)
        checked = sum(1 for i in self._files.values()
                      if i["item"].checkState() == Qt.Checked)
        self.label_count.setText(f"已选 {checked} / {total} 个文件")
        self.btn_start.setEnabled(checked > 0 and not self._exporting and
                                  any(i["state"] == "ok" for i in self._files.values()))

    def _requeue_parse(self, path: str, info: dict) -> None:
        info["state"] = "pending"
        info["item"].setData(ROLE_STATE, "pending")
        info["item"].setData(ROLE_STATUS, "重新解析…")
        self.parse_worker.request_parse(Path(path))

    # ------------------------------------------------------------------ #
    # 解析回调
    # ------------------------------------------------------------------ #
    def _on_parsed(self, path_str: str, pages: int, width_pt: int, height_pt: int) -> None:
        key = str(Path(path_str).resolve())
        info = self._files.get(key)
        if info is None:
            return
        info.update(pages=pages, w=width_pt, h=height_pt, state="ok")
        item = info["item"]
        item.setData(ROLE_STATE, "ok")
        item.setData(ROLE_PAGES, pages)
        mm_w = width_pt / 72.0 * 25.4
        mm_h = height_pt / 72.0 * 25.4
        item.setData(ROLE_STATUS, f"{pages} 页 · {mm_w:.0f}×{mm_h:.0f} mm")

        self._update_counts()
        if self._current_path == key:
            self._apply_current_document()

    def _on_parse_failed(self, path_str: str, message: str) -> None:
        key = str(Path(path_str).resolve())
        info = self._files.get(key)
        if info is None:
            return
        info["state"] = "error"
        item = info["item"]
        item.setData(ROLE_STATE, "error")
        item.setData(ROLE_STATUS, message)
        self._log(f"✗ {Path(path_str).name}：{message}")
        if self._current_path == key:
            self.preview.show_message("该文件无法打开\n" + message)
        self._update_counts()

    # ------------------------------------------------------------------ #
    # 预览
    # ------------------------------------------------------------------ #
    def _on_selection_changed(self) -> None:
        items = self.file_list.selectedItems()
        if not items:
            return
        key = str(Path(items[0].data(Qt.UserRole)).resolve())
        if key == self._current_path:
            return
        self._current_path = key
        self._current_page = 1
        self._apply_current_document()

    def _apply_current_document(self) -> None:
        if not self._current_path:
            return
        info = self._files.get(self._current_path)
        if info is None:
            return

        name = info["path"].name
        self.preview_title.setText(name)
        self.preview_title.setToolTip(str(info["path"]))

        if info["state"] == "pending":
            self.preview.show_message("正在解析…")
            self.btn_export_this.setEnabled(False)
            return
        if info["state"] == "error":
            self.btn_export_this.setEnabled(False)
            return

        pages = max(1, info["pages"])
        self.btn_export_this.setEnabled(True)
        self.spin_page.blockSignals(True)
        self.spin_page.setRange(1, pages)
        self.spin_page.setValue(min(self._current_page, pages))
        self.spin_page.blockSignals(False)
        self.label_total.setText(f"/ {pages}")
        self.label_page_badge.setText(f"第 {self._current_page} 页，共 {pages} 页")

        self.settings.set_estimate(info["w"], info["h"], info["pages"])
        self._goto_page(self._current_page)

    def _step_page(self, delta: int) -> None:
        if not self._current_path:
            return
        info = self._files.get(self._current_path)
        if not info or info["state"] != "ok":
            return
        target = min(max(1, self._current_page + delta), max(1, info["pages"]))
        self._goto_page(target)

    def _on_page_spin(self, value: int) -> None:
        self._goto_page(value)

    def _goto_page(self, page: int) -> None:
        if not self._current_path:
            return
        info = self._files.get(self._current_path)
        if not info or info["state"] != "ok":
            return
        page = min(max(1, page), max(1, info["pages"]))
        self._current_page = page
        self.spin_page.blockSignals(True)
        self.spin_page.setValue(page)
        self.spin_page.blockSignals(False)
        self.label_page_badge.setText(f"第 {page} 页，共 {info['pages']} 页")
        self.settings.set_estimate(info["w"], info["h"], info["pages"])

        cached = self._pix_cache.get((self._current_path, page))
        if cached is not None:
            self.preview.set_image(cached)
            return

        self.preview.show_message("正在渲染…")
        self.parse_worker.request_preview(Path(self._current_path), page)

    def _on_preview_ready(self, path_str: str, page: int, data: bytes) -> None:
        key = str(Path(path_str).resolve())
        pixmap = QPixmap()
        if not pixmap.loadFromData(data):
            self.preview.show_message("预览渲染失败")
            return
        if len(self._pix_cache) > 80:
            self._pix_cache.clear()
        self._pix_cache[(key, page)] = pixmap
        if key == self._current_path and page == self._current_page:
            self.preview.set_image(pixmap)

    def _refresh_estimate(self) -> None:
        if not self._current_path:
            return
        info = self._files.get(self._current_path)
        if info and info["state"] == "ok":
            self.settings.set_estimate(info["w"], info["h"], info["pages"])
        self._update_counts()

    # ------------------------------------------------------------------ #
    # 导出
    # ------------------------------------------------------------------ #
    def _start_export(self, only_current: bool) -> None:
        if self._exporting:
            return

        render_opt = self.settings.render_options()
        page_mode = self.settings.page_mode()
        spec = self.settings.page_spec()

        if page_mode == "range":
            problem = validate_page_spec(spec)
            if problem:
                QMessageBox.warning(self, "页码格式有误", problem)
                self.settings.edit_page_spec.setFocus()
                return

        tasks: list[FileTask] = []
        if only_current:
            if not self._current_path:
                return
            info = self._files.get(self._current_path)
            if not info or info["state"] != "ok":
                QMessageBox.information(self, "提示", "当前文件还没有解析完成")
                return
            tasks.append(FileTask(Path(self._current_path), "current", "", self._current_page))
        else:
            for key, info in self._files.items():
                if info["item"].checkState() != Qt.Checked:
                    continue
                if info["state"] == "pending":
                    QMessageBox.information(self, "提示", "还有文件正在解析，请稍候再导出")
                    return
                if info["state"] == "ok":
                    tasks.append(FileTask(Path(key), page_mode, spec,
                                          self._current_page if key == self._current_path else 1))
            if not tasks:
                QMessageBox.information(self, "提示", "请先勾选要导出的文件")
                return

        out_text = self.settings.out_dir_text()
        if out_text:
            out_dir = Path(out_text)
        else:
            # 留空表示跟随源文件：导出到「源文件目录 / 导出图片」
            out_dir = Path(tasks[0].path).parent / "导出图片"

        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            QMessageBox.critical(self, "无法创建输出目录", str(exc))
            return

        self._last_outdir = str(out_dir)

        # 导出时自动展开日志，方便观察进度
        if not self.log_box.isVisible():
            self.btn_log.setChecked(True)

        self._log("")
        self._log(f"开始导出：{len(tasks)} 个文件 → {out_dir}")
        self._log(f"参数：{render_opt.fmt} · "
                  f"{'DPI ' + str(render_opt.dpi) if render_opt.size_mode == 'dpi' else ('宽 ' + str(render_opt.width_px) + 'px' if render_opt.size_mode == 'width' else '高 ' + str(render_opt.height_px) + 'px')}"
                  f" · 背景 {render_opt.background} · 页码 {page_mode}")

        self.export_worker = ExportWorker(
            self._loader, tasks, render_opt, out_dir,
            self.settings.subfolder(), self.settings.template(),
            self.settings.conflict(), self._engine, self)
        self.export_worker.progress.connect(self._on_export_progress)
        self.export_worker.file_done.connect(self._on_file_done)
        self.export_worker.failed.connect(self._on_export_failed)
        self.export_worker.finished_all.connect(self._on_export_finished)

        self._set_exporting(True)
        self.progress.setValue(0)
        self.export_worker.start()

    def _set_exporting(self, active: bool) -> None:
        self._exporting = active
        self.btn_start.setVisible(not active)
        self.btn_cancel.setVisible(active)
        self.btn_add.setEnabled(not active)
        self.btn_remove.setEnabled(not active)
        self.btn_clear.setEnabled(not active)
        self.settings.setEnabled(not active)
        info = self._files.get(self._current_path) if self._current_path else None
        self.btn_export_this.setEnabled(
            not active and bool(info) and info.get("state") == "ok")
        if not active:
            self._update_counts()

    def _on_export_progress(self, done: int, total: int, name: str) -> None:
        percent = int(done / max(1, total) * 100)
        self.progress.setValue(percent)
        self.label_status.setText(f"正在导出 {done}/{total} · {name}")

    def _on_file_done(self, path_str: str, count: int) -> None:
        self._log(f"✓ {Path(path_str).name}：{count} 张")

    def _on_export_failed(self, path_str: str, message: str) -> None:
        self._log(f"✗ {Path(path_str).name}：{message}")

    def _on_export_finished(self, files: int, images: int, outdir: str) -> None:
        self._set_exporting(False)
        self.progress.setValue(100 if images else 0)
        self.label_status.setText(f"完成：{files} 个文件，共 {images} 张图片")
        self.btn_open.setEnabled(bool(images))
        self._log(f"导出结束：{files} 个文件，{images} 张图片")
        self._log(f"输出目录：{outdir}")

    def _cancel_export(self) -> None:
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.cancel()
            self.label_status.setText("正在取消…")
            self._log("用户取消导出")

    def _open_outdir(self) -> None:
        target = self._last_outdir or self.settings.out_dir_text()
        if not target:
            return
        path = Path(target)
        if not path.exists():
            QMessageBox.information(self, "目录不存在", str(path))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    # ------------------------------------------------------------------ #
    # 杂项
    # ------------------------------------------------------------------ #
    def _toggle_log(self, checked: bool) -> None:
        self.log_box.setVisible(checked)
        if checked:
            self.log_box.ensureCursorVisible()

    def _log(self, text: str) -> None:
        if not text:
            self.log_box.appendPlainText("")
            return
        self.log_box.appendPlainText(text)

    def dragEnterEvent(self, event) -> None:  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # noqa: N802
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if paths:
            self.add_files(paths)
            event.acceptProposedAction()

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._exporting and self.export_worker:
            self.export_worker.cancel()
            if not self.export_worker.wait(4000):
                self.export_worker.terminate()
                self.export_worker.wait(1000)
        self.settings.save_settings()
        if hasattr(self, "parse_worker") and self.parse_worker.isRunning():
            self.parse_worker.request_stop()
            if not self.parse_worker.wait(4000):
                self.parse_worker.terminate()
                self.parse_worker.wait(1000)
        super().closeEvent(event)
