# -*- coding: utf-8 -*-
"""界面主题：配色常量与全局样式表。"""

from __future__ import annotations

# ---- 配色（浅色主题）------------------------------------------------------ #
BG = "#F2F4F7"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F9FAFB"
BORDER = "#E4E7EC"
BORDER_STRONG = "#D0D5DD"
TEXT = "#17202E"
TEXT_MUTED = "#667085"
TEXT_FAINT = "#98A2B3"
PRIMARY = "#2A6DF4"
PRIMARY_HOVER = "#1E5BD6"
PRIMARY_PRESSED = "#1849AE"
PRIMARY_SOFT = "#EAF1FE"
SUCCESS = "#12B76A"
WARNING = "#F79009"
DANGER = "#F04438"

QSS = f"""
* {{
    font-family: "Microsoft YaHei UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    outline: none;
}}

QWidget {{
    color: {TEXT};
    font-size: 13px;
}}

QMainWindow, #Root {{
    background: {BG};
}}

/* ---------- 顶部 ---------- */
#Header {{
    background: {SURFACE};
    border-bottom: 1px solid {BORDER};
}}
#AppTitle {{
    font-size: 17px;
    font-weight: 600;
    color: {TEXT};
}}
#AppSubtitle {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QPushButton#EngineChip {{
    background: {PRIMARY_SOFT};
    color: {PRIMARY};
    border: none;
    border-radius: 12px;
    padding: 5px 14px;
    font-size: 12px;
}}
QPushButton#EngineChip:hover {{
    background: #DDE9FD;
}}
QPushButton#EngineChip[state="warn"] {{
    background: #FEF3E2;
    color: {WARNING};
}}
QPushButton#EngineChip[state="error"] {{
    background: #FEE4E2;
    color: {DANGER};
}}

/* ---------- 卡片 ---------- */
#Card {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 10px;
}}
#CardTitle {{
    font-size: 13px;
    font-weight: 600;
    color: {TEXT};
}}
#CardHint {{
    font-size: 11px;
    color: {TEXT_FAINT};
}}
#FieldLabel {{
    font-size: 12px;
    color: {TEXT_MUTED};
}}
#SectionLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {TEXT_FAINT};
    letter-spacing: 1px;
}}

/* ---------- 按钮 ---------- */
QPushButton {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 7px;
    padding: 7px 14px;
    color: {TEXT};
}}
QPushButton:hover {{
    background: {SURFACE_ALT};
    border-color: #B9C0CC;
}}
QPushButton:pressed {{
    background: #EEF0F4;
}}
QPushButton:disabled {{
    color: {TEXT_FAINT};
    border-color: {BORDER};
    background: {SURFACE_ALT};
}}

QPushButton#Primary {{
    background: {PRIMARY};
    border: 1px solid {PRIMARY};
    color: #FFFFFF;
    font-weight: 600;
    padding: 9px 22px;
}}
QPushButton#Primary:hover {{
    background: {PRIMARY_HOVER};
    border-color: {PRIMARY_HOVER};
}}
QPushButton#Primary:pressed {{
    background: {PRIMARY_PRESSED};
}}
QPushButton#Primary:disabled {{
    background: #B9CCF7;
    border-color: #B9CCF7;
    color: #FFFFFF;
}}

QPushButton#Ghost {{
    background: transparent;
    border: 1px solid transparent;
    color: {TEXT_MUTED};
    padding: 6px 12px;
}}
QPushButton#Ghost:hover {{
    background: {SURFACE_ALT};
    color: {TEXT};
}}
QPushButton#Ghost:checked {{
    background: {PRIMARY_SOFT};
    color: {PRIMARY};
}}
QPushButton#Chip {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    color: {TEXT_MUTED};
}}
QPushButton#Chip:hover {{
    background: {PRIMARY_SOFT};
    border-color: {PRIMARY_SOFT};
    color: {PRIMARY};
}}

/* ---------- 滑块 ---------- */
QSlider::groove:horizontal {{
    height: 4px;
    background: #E9EDF3;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {PRIMARY};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 9px;
    height: 9px;
    margin: -5px 0;
    border-radius: 7px;
    background: {SURFACE};
    border: 2px solid {PRIMARY};
}}
QSlider::handle:horizontal:hover {{
    background: {PRIMARY_SOFT};
}}
QSlider:disabled::sub-page:horizontal {{
    background: {BORDER_STRONG};
}}
QSlider:disabled::handle:horizontal {{
    border-color: {BORDER_STRONG};
}}
QPushButton#IconButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 14px;
    color: {TEXT_MUTED};
}}
QPushButton#IconButton:hover {{
    background: {PRIMARY_SOFT};
    color: {PRIMARY};
}}

/* ---------- 输入控件 ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background: {SURFACE};
    border: 1px solid {BORDER_STRONG};
    border-radius: 7px;
    padding: 6px 9px;
    selection-background-color: {PRIMARY};
    selection-color: #FFFFFF;
    min-height: 20px;
}}
QLineEdit:hover, QComboBox:hover, QSpinBox:hover {{
    border-color: #B9C0CC;
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {PRIMARY};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled {{
    background: {SURFACE_ALT};
    color: {TEXT_FAINT};
}}
QLineEdit[state="error"] {{
    border-color: {DANGER};
    background: #FFF5F4;
}}

QComboBox::drop-down {{
    border: none;
    width: 22px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {TEXT_MUTED};
    margin-right: 7px;
}}
QComboBox QAbstractItemView {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 4px;
    selection-background-color: {PRIMARY_SOFT};
    selection-color: {PRIMARY};
    outline: none;
}}

QSpinBox::up-button, QSpinBox::down-button {{
    width: 16px;
    border: none;
    background: transparent;
}}

/* ---------- 复选框（沿用 Fusion 原生指示器，自带对勾）---------- */
QCheckBox {{
    spacing: 8px;
    color: {TEXT};
    padding: 2px 0;
}}

/* ---------- 列表 ---------- */
QListWidget {{
    background: transparent;
    border: none;
    outline: none;
}}
QListWidget::item {{
    border-radius: 8px;
}}
QListWidget::item:selected {{
    background: {PRIMARY_SOFT};
}}

/* ---------- 滚动条 ---------- */
QScrollArea {{
    background: transparent;
    border: none;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 9px;
    margin: 2px 1px;
}}
QScrollBar::handle:vertical {{
    background: #D5DAE3;
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{
    background: #BAC2D0;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: transparent;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 9px;
    margin: 1px 2px;
}}
QScrollBar::handle:horizontal {{
    background: #D5DAE3;
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
}}

/* ---------- 进度条 ---------- */
QProgressBar {{
    background: #EDEFF3;
    border: none;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    color: transparent;
}}
QProgressBar::chunk {{
    background: {PRIMARY};
    border-radius: 4px;
}}

/* ---------- 预览 ---------- */
#PreviewStage {{
    background: #EDEFF3;
    border-radius: 8px;
}}
#PreviewEmpty {{
    color: {TEXT_FAINT};
    font-size: 13px;
}}
#PageBadge {{
    background: rgba(23, 32, 46, 0.72);
    color: #FFFFFF;
    border-radius: 9px;
    padding: 3px 9px;
    font-size: 11px;
}}

/* ---------- 日志 ---------- */
QPlainTextEdit#Log {{
    background: {SURFACE_ALT};
    border: 1px solid {BORDER};
    border-radius: 8px;
    color: #4B5563;
    font-family: "Consolas", "Microsoft YaHei UI", monospace;
    font-size: 12px;
    padding: 7px;
}}

/* ---------- 分割条 ---------- */
QSplitter::handle {{
    background: transparent;
    width: 10px;
}}

QToolTip {{
    background: #1F2937;
    color: #FFFFFF;
    border: none;
    padding: 5px 8px;
    border-radius: 5px;
}}
"""
