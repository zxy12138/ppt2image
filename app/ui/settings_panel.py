# -*- coding: utf-8 -*-
"""右侧参数面板：导出范围、输出格式、分辨率、输出位置。

布局刻意做紧凑（标签与控件同一行），保证在 1280×800 级别窗口里
四组设置不用滚动太多。
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea,
                               QSlider, QSpinBox, QVBoxLayout, QWidget)

from ..converter import RenderOptions
from .widgets import Card, field_label


class SettingsPanel(QScrollArea):
    """可滚动设置面板。"""

    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QScrollArea.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 6, 8)
        layout.setSpacing(8)

        # 最常用的放最上面
        layout.addWidget(self._build_range_card())
        layout.addWidget(self._build_output_card())
        layout.addWidget(self._build_format_card())
        layout.addWidget(self._build_size_card())
        layout.addStretch(1)
        self.setWidget(container)

        self.setMinimumWidth(318)
        # 三种尺寸方式各自记住上次的值，切换时不互相踩踏
        self._size_values = {"dpi": 150, "width": 1920, "height": 1080}
        self._last_mode = "dpi"
        self._connect()
        self._apply_state()
        self.load_settings()

    # ------------------------------------------------------------------ #
    # 工具
    # ------------------------------------------------------------------ #
    @staticmethod
    def _row(text: str, widget: QWidget, label_width: int = 40) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        label = QLabel(text)
        label.setObjectName("FieldLabel")
        label.setFixedWidth(label_width)
        layout.addWidget(label)
        layout.addWidget(widget, 1)
        return row

    # ------------------------------------------------------------------ #
    # 卡片构建
    # ------------------------------------------------------------------ #
    def _build_range_card(self) -> Card:
        card = Card("导出范围")
        body = card.body()

        self.combo_page_mode = QComboBox()
        self.combo_page_mode.addItem("全部页面", "all")
        self.combo_page_mode.addItem("当前预览页", "current")
        self.combo_page_mode.addItem("指定页码", "range")
        self.combo_page_mode.setToolTip(
            "全部页面：每个文件逐页导出\n"
            "当前预览页：只导出中间预览的那一页（多文件时仅对选中的文件生效）\n"
            "指定页码：按下方填写的页码导出，例如 1,3,5-9")
        body.addWidget(self._row("页码", self.combo_page_mode))

        self.edit_page_spec = QLineEdit()
        self.edit_page_spec.setPlaceholderText("例如 1,3,5-9")
        body.addWidget(self.edit_page_spec)
        return card

    def _build_format_card(self) -> Card:
        card = Card("输出格式")
        body = card.body()

        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["PNG", "JPG", "WEBP"])
        self.combo_fmt.setToolTip("PNG 无损清晰；JPG 体积小；WEBP 体积最小")
        body.addWidget(self._row("格式", self.combo_fmt))

        self.combo_bg = QComboBox()
        self.combo_bg.addItem("白色背景", "white")
        self.combo_bg.addItem("黑色背景", "black")
        self.combo_bg.addItem("透明背景", "transparent")
        body.addWidget(self._row("背景", self.combo_bg))

        slider_box = QWidget()
        slider_layout = QHBoxLayout(slider_box)
        slider_layout.setContentsMargins(0, 0, 0, 0)
        slider_layout.setSpacing(8)
        self.slider_quality = QSlider(Qt.Horizontal)
        self.slider_quality.setRange(40, 100)
        self.slider_quality.setValue(92)
        self.label_quality_value = QLabel("92")
        self.label_quality_value.setObjectName("CardHint")
        self.label_quality_value.setFixedWidth(22)
        self.label_quality_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        slider_layout.addWidget(self.slider_quality, 1)
        slider_layout.addWidget(self.label_quality_value)
        body.addWidget(self._row("画质", slider_box))
        return card

    def _build_size_card(self) -> Card:
        card = Card("分辨率")
        body = card.body()

        self.combo_size_mode = QComboBox()
        self.combo_size_mode.addItem("按 DPI", "dpi")
        self.combo_size_mode.addItem("按宽度", "width")
        self.combo_size_mode.addItem("按高度", "height")
        body.addWidget(self._row("尺寸", self.combo_size_mode))

        self.spin_size = QSpinBox()
        self.spin_size.setRange(48, 600)
        self.spin_size.setValue(150)
        self.spin_size.setSingleStep(10)
        self.spin_size.setMinimumWidth(80)
        self.spin_size.setToolTip("DPI 越高越清晰，体积也越大")

        self.label_size_unit = field_label("DPI")
        self.label_size_unit.setFixedWidth(26)
        size_box = QWidget()
        size_layout = QHBoxLayout(size_box)
        size_layout.setContentsMargins(0, 0, 0, 0)
        size_layout.setSpacing(6)
        size_layout.addWidget(self.spin_size, 1)
        size_layout.addWidget(self.label_size_unit)
        body.addWidget(self._row("数值", size_box))

        presets = QHBoxLayout()
        presets.setContentsMargins(48, 0, 0, 0)
        presets.setSpacing(6)
        for text, dpi in (("96", 96), ("150", 150), ("200", 200), ("300", 300)):
            btn = QPushButton(text)
            btn.setObjectName("Chip")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, d=dpi: self._apply_dpi_preset(d))
            presets.addWidget(btn)
        presets.addStretch(1)
        body.addLayout(presets)

        self.label_estimate = QLabel("—")
        self.label_estimate.setObjectName("CardHint")
        self.label_estimate.setWordWrap(True)
        body.addWidget(self.label_estimate)
        return card

    def _build_output_card(self) -> Card:
        card = Card("输出位置")
        body = card.body()

        dir_box = QWidget()
        dir_layout = QHBoxLayout(dir_box)
        dir_layout.setContentsMargins(0, 0, 0, 0)
        dir_layout.setSpacing(6)
        self.edit_outdir = QLineEdit()
        self.edit_outdir.setPlaceholderText("默认：源文件目录 / 导出图片")
        self.btn_browse = QPushButton("浏览")
        self.btn_browse.setCursor(Qt.PointingHandCursor)
        dir_layout.addWidget(self.edit_outdir, 1)
        dir_layout.addWidget(self.btn_browse)
        body.addWidget(dir_box)

        self.check_subfolder = QCheckBox("每个文件建子文件夹")
        self.check_subfolder.setChecked(True)

        self.combo_conflict = QComboBox()
        self.combo_conflict.addItem("同名自动编号", "rename")
        self.combo_conflict.addItem("覆盖已有", "overwrite")
        self.combo_conflict.addItem("跳过已有", "skip")
        self.combo_conflict.setFixedWidth(118)
        self.combo_conflict.setToolTip("目标目录已存在同名图片时的处理方式")

        opt_row = QWidget()
        opt_layout = QHBoxLayout(opt_row)
        opt_layout.setContentsMargins(0, 0, 0, 0)
        opt_layout.setSpacing(6)
        opt_layout.addWidget(self.check_subfolder)
        opt_layout.addStretch(1)
        opt_layout.addWidget(self.combo_conflict)
        body.addWidget(opt_row)

        self.edit_template = QLineEdit("{name}_{page:03d}")
        self.edit_template.setToolTip(
            "可用占位符：{name} 文件名　{page} 页码　{index} 序号　{total} 总页数\n"
            "补零写法 {page:03d} → 001")
        body.addWidget(self._row("命名", self.edit_template, 40))
        return card

    # ------------------------------------------------------------------ #
    # 交互
    # ------------------------------------------------------------------ #
    def _connect(self) -> None:
        self.combo_fmt.currentIndexChanged.connect(self._apply_state)
        self.combo_size_mode.currentIndexChanged.connect(self._apply_state)
        self.combo_page_mode.currentIndexChanged.connect(self._apply_state)
        self.slider_quality.valueChanged.connect(self._on_quality)
        self.spin_size.valueChanged.connect(self._emit_changed)
        self.combo_bg.currentIndexChanged.connect(self._emit_changed)
        self.combo_conflict.currentIndexChanged.connect(self._emit_changed)
        self.edit_template.textChanged.connect(self._emit_changed)
        self.edit_page_spec.textChanged.connect(self._emit_changed)
        self.edit_outdir.textChanged.connect(self._emit_changed)
        self.check_subfolder.toggled.connect(self._emit_changed)
        self.btn_browse.clicked.connect(self._browse_outdir)

    def _emit_changed(self, *_args) -> None:
        self.changed.emit()

    def _apply_dpi_preset(self, dpi: int) -> None:
        self.combo_size_mode.setCurrentIndex(0)
        self.spin_size.setValue(dpi)

    def _on_quality(self, value: int) -> None:
        self.label_quality_value.setText(str(value))
        self._emit_changed()

    def _browse_outdir(self) -> None:
        start = self.edit_outdir.text().strip() or str(Path.home())
        path = QFileDialog.getExistingDirectory(self, "选择输出目录", start)
        if path:
            self.edit_outdir.setText(path)

    def _apply_state(self, *_args) -> None:
        fmt = self.combo_fmt.currentText()
        lossy = fmt in ("JPG", "WEBP")
        self.slider_quality.setEnabled(lossy)
        self.label_quality_value.setEnabled(lossy)

        if self.combo_bg.currentData() == "transparent" and lossy:
            self.combo_bg.setCurrentIndex(0)

        mode = self.combo_size_mode.currentData()
        if mode != self._last_mode:
            self._size_values[self._last_mode] = self.spin_size.value()
            self._last_mode = mode

        self.spin_size.blockSignals(True)
        if mode == "dpi":
            self.spin_size.setRange(48, 600)
            self.spin_size.setSingleStep(10)
            self.label_size_unit.setText("DPI")
        else:
            self.spin_size.setRange(200, 16000)
            self.spin_size.setSingleStep(100)
            self.label_size_unit.setText("px")
        self.spin_size.setValue(self._size_values.get(mode, 150))
        self.spin_size.blockSignals(False)

        self.edit_page_spec.setVisible(self.combo_page_mode.currentData() == "range")
        self._emit_changed()

    # ------------------------------------------------------------------ #
    # 取值
    # ------------------------------------------------------------------ #
    def render_options(self) -> RenderOptions:
        mode = self.combo_size_mode.currentData()
        value = self.spin_size.value()
        return RenderOptions(
            fmt=self.combo_fmt.currentText(),
            size_mode=mode,
            dpi=value if mode == "dpi" else 150,
            width_px=value if mode == "width" else 1920,
            height_px=value if mode == "height" else 1080,
            background=self.combo_bg.currentData(),
            quality=self.slider_quality.value(),
        )

    def page_mode(self) -> str:
        return str(self.combo_page_mode.currentData())

    def page_spec(self) -> str:
        return self.edit_page_spec.text().strip()

    def out_dir_text(self) -> str:
        return self.edit_outdir.text().strip()

    def subfolder(self) -> bool:
        return self.check_subfolder.isChecked()

    def template(self) -> str:
        return self.edit_template.text()

    def conflict(self) -> str:
        return str(self.combo_conflict.currentData())

    # ------------------------------------------------------------------ #
    # 尺寸预估
    # ------------------------------------------------------------------ #
    def set_estimate(self, width_pt: float, height_pt: float, pages: int = 0) -> None:
        if width_pt <= 0 or height_pt <= 0:
            self.label_estimate.setText("—")
            return
        opt = self.render_options()
        if opt.size_mode == "width":
            w = opt.width_px
            h = int(round(w * height_pt / width_pt))
        elif opt.size_mode == "height":
            h = opt.height_px
            w = int(round(h * width_pt / height_pt))
        else:
            w = int(round(width_pt / 72.0 * opt.dpi))
            h = int(round(height_pt / 72.0 * opt.dpi))
        extra = f" · 共 {pages} 页" if pages else ""
        self.label_estimate.setText(f"输出：{w} × {h} px{extra}")

    # ------------------------------------------------------------------ #
    # 配置持久化
    # ------------------------------------------------------------------ #
    def _settings(self) -> QSettings:
        return QSettings("PPT2Image", "PPT2Image")

    def save_settings(self) -> None:
        s = self._settings()
        s.setValue("fmt", self.combo_fmt.currentText())
        s.setValue("bg", self.combo_bg.currentData())
        s.setValue("quality", self.slider_quality.value())
        s.setValue("size_mode", self.combo_size_mode.currentData())
        s.setValue("size_value", self.spin_size.value())
        s.setValue("page_mode", self.combo_page_mode.currentData())
        s.setValue("page_spec", self.edit_page_spec.text())
        s.setValue("subfolder", self.check_subfolder.isChecked())
        s.setValue("template", self.edit_template.text())
        s.setValue("conflict", self.combo_conflict.currentData())
        s.setValue("outdir", self.edit_outdir.text())

    def load_settings(self) -> None:
        s = self._settings()
        widgets = [self.combo_fmt, self.combo_bg, self.combo_size_mode,
                   self.combo_page_mode, self.combo_conflict]
        for w in widgets:
            w.blockSignals(True)

        fmt = s.value("fmt", "PNG", type=str)
        if fmt in ("PNG", "JPG", "WEBP"):
            self.combo_fmt.setCurrentText(fmt)

        bg = s.value("bg", "white", type=str)
        index = self.combo_bg.findData(bg)
        if index >= 0:
            self.combo_bg.setCurrentIndex(index)

        self.slider_quality.setValue(s.value("quality", 92, type=int))
        self.label_quality_value.setText(str(self.slider_quality.value()))

        mode = s.value("size_mode", "dpi", type=str)
        index = self.combo_size_mode.findData(mode)
        if index >= 0:
            self.combo_size_mode.setCurrentIndex(index)

        pm = s.value("page_mode", "all", type=str)
        index = self.combo_page_mode.findData(pm)
        if index >= 0:
            self.combo_page_mode.setCurrentIndex(index)

        cf = s.value("conflict", "rename", type=str)
        index = self.combo_conflict.findData(cf)
        if index >= 0:
            self.combo_conflict.setCurrentIndex(index)

        self.edit_page_spec.setText(s.value("page_spec", "1-3", type=str))
        self.check_subfolder.setChecked(s.value("subfolder", True, type=bool))
        self.edit_template.setText(s.value("template", "{name}_{page:03d}", type=str))
        self.edit_outdir.setText(s.value("outdir", "", type=str))

        for w in widgets:
            w.blockSignals(False)

        # 尺寸值要在模式确定后再设，避免范围裁切
        self._apply_state()
        value = s.value("size_value", 150, type=int)
        self.spin_size.setValue(value)
        self._size_values[self.combo_size_mode.currentData()] = self.spin_size.value()
