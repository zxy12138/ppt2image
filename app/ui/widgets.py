# -*- coding: utf-8 -*-
"""自定义控件：卡片、文件列表绘制、自适应预览。"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import (QColor, QFont, QFontMetrics, QPainter, QPen, QPixmap)
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget,
                               QListWidgetItem, QStyle, QStyledItemDelegate,
                               QVBoxLayout, QWidget)

from . import theme

# 列表项数据角色
ROLE_PAGES = Qt.UserRole + 1
ROLE_STATUS = Qt.UserRole + 2
ROLE_STATE = Qt.UserRole + 3      # ok / pending / error
ROLE_KIND = Qt.UserRole + 4


class Card(QFrame):
    """白色圆角卡片，带标题与可选说明。"""

    def __init__(self, title: str = "", hint: str = "", parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("Card")
        outer = QVBoxLayout(self)
        outer.setContentsMargins(13, 11, 13, 12)
        outer.setSpacing(8)

        if title:
            head = QHBoxLayout()
            head.setSpacing(6)
            label = QLabel(title)
            label.setObjectName("CardTitle")
            head.addWidget(label)
            head.addStretch(1)
            if hint:
                hint_label = QLabel(hint)
                hint_label.setObjectName("CardHint")
                head.addWidget(hint_label)
            outer.addLayout(head)

        self._body = QVBoxLayout()
        self._body.setContentsMargins(0, 0, 0, 0)
        self._body.setSpacing(8)
        outer.addLayout(self._body)

    def body(self) -> QVBoxLayout:
        return self._body

    def add(self, widget: QWidget) -> QWidget:
        self._body.addWidget(widget)
        return widget


def field_label(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("FieldLabel")
    return label


def _is_checked(value) -> bool:
    """兼容 PySide6 中 CheckState 可能是枚举或 int 的两种返回。"""
    if value is None:
        return False
    if isinstance(value, int):
        return value == 2          # Qt.Checked
    return getattr(value, "value", value) == 2


class FileDelegate(QStyledItemDelegate):
    """文件列表项：自绘复选框 + 类型徽章 + 文件名 + 状态行。"""

    BADGE_COLORS = {
        "PDF": ("#FEF3F2", "#D92D20"),
        "PPT": ("#FFF4ED", "#E04F16"),
        "PPTX": ("#FFF4ED", "#E04F16"),
        "ODP": ("#EEF4FF", "#2A6DF4"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hover_row = -1

    # -- 尺寸 ------------------------------------------------------------- #
    def sizeHint(self, option, index) -> QSize:  # noqa: N802
        return QSize(option.rect.width(), 58)

    @staticmethod
    def _checkbox_rect(rect) -> QRectF:
        return QRectF(rect.left() + 10, rect.center().y() - 8, 16, 16)

    # -- 绘制 ------------------------------------------------------------- #
    def paint(self, painter: QPainter, option, index) -> None:  # noqa: N802
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = QRectF(option.rect).adjusted(4, 2, -4, -2)
        selected = bool(option.state & QStyle.State_Selected)
        hovered = bool(option.state & QStyle.State_MouseOver)

        if selected:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.PRIMARY_SOFT))
            painter.drawRoundedRect(rect, 8, 8)
        elif hovered:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.SURFACE_ALT))
            painter.drawRoundedRect(rect, 8, 8)

        # ---- 复选框 ----
        cb = self._checkbox_rect(option.rect)
        checked = _is_checked(index.data(Qt.CheckStateRole))
        if checked:
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(theme.PRIMARY))
            painter.drawRoundedRect(cb, 4, 4)
            pen = QPen(QColor("#FFFFFF"), 1.8)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            p1 = QPointF(cb.left() + 3.6, cb.top() + 8.2)
            p2 = QPointF(cb.left() + 6.8, cb.top() + 11.4)
            p3 = QPointF(cb.left() + 12.4, cb.top() + 5.0)
            painter.drawLine(p1, p2)
            painter.drawLine(p2, p3)
        else:
            painter.setPen(QPen(QColor(theme.BORDER_STRONG), 1.4))
            painter.setBrush(QColor(theme.SURFACE))
            painter.drawRoundedRect(cb, 4, 4)

        # ---- 类型徽章 ----
        kind = str(index.data(ROLE_KIND) or "")
        badge = self.BADGE_COLORS.get(kind, ("#F2F4F7", "#667085"))
        badge_rect = QRectF(cb.right() + 10, option.rect.center().y() - 9, 34, 18)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(badge[0]))
        painter.drawRoundedRect(badge_rect, 5, 5)
        bfont = QFont(painter.font())
        bfont.setPointSizeF(7.5)
        bfont.setBold(True)
        painter.setFont(bfont)
        painter.setPen(QColor(badge[1]))
        painter.drawText(badge_rect, Qt.AlignCenter, kind or "FILE")

        # ---- 文本 ----
        text_left = int(badge_rect.right() + 10)
        text_right = int(rect.right() - 10)
        name = str(index.data(Qt.DisplayRole) or "")
        state = str(index.data(ROLE_STATE) or "ok")
        status = str(index.data(ROLE_STATUS) or "")

        name_font = QFont(painter.font())
        name_font.setPointSizeF(9.5)
        name_font.setBold(False)
        painter.setFont(name_font)
        painter.setPen(QColor(theme.TEXT))
        fm = QFontMetrics(name_font)
        name_rect = QRectF(text_left, option.rect.center().y() - 19,
                           max(10, text_right - text_left), 18)
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter,
                         fm.elidedText(name, Qt.ElideMiddle, int(name_rect.width())))

        status_font = QFont(painter.font())
        status_font.setPointSizeF(8)
        painter.setFont(status_font)
        color = {"ok": theme.TEXT_MUTED, "pending": theme.WARNING,
                 "error": theme.DANGER}.get(state, theme.TEXT_MUTED)
        painter.setPen(QColor(color))
        fm2 = QFontMetrics(status_font)
        status_rect = QRectF(text_left, option.rect.center().y() + 1,
                             max(10, text_right - text_left), 17)
        painter.drawText(status_rect, Qt.AlignLeft | Qt.AlignVCenter,
                         fm2.elidedText(status, Qt.ElideRight, int(status_rect.width())))

        painter.restore()

    # -- 交互：点击复选框切换勾选 ------------------------------------------ #
    def editorEvent(self, event, model, option, index) -> bool:  # noqa: N802
        if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
            if self._checkbox_rect(option.rect).contains(event.pos()):
                new_state = Qt.Unchecked if _is_checked(index.data(Qt.CheckStateRole)) else Qt.Checked
                model.setData(index, new_state, Qt.CheckStateRole)
                return True
        return super().editorEvent(event, model, option, index)


class FileList(QListWidget):
    """文件列表，支持拖放由主窗口统一处理。"""

    item_check_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(FileDelegate(self))
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setSelectionMode(QListWidget.SingleSelection)
        self.setSpacing(0)
        self.itemChanged.connect(lambda _: self.item_check_changed.emit())

    def add_file(self, path_str: str, kind: str) -> QListWidgetItem:
        item = QListWidgetItem(path_str.rsplit("/", 1)[-1])
        item.setData(Qt.UserRole, path_str)
        item.setData(ROLE_KIND, kind)
        item.setData(ROLE_STATE, "pending")
        item.setData(ROLE_STATUS, "正在解析…")
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked)
        self.addItem(item)
        return item


class PreviewView(QLabel):
    """按比例缩放显示图片的预览控件。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(240, 160)
        self.setObjectName("PreviewStage")
        self._source: QPixmap | None = None
        self._padding = 18

    def set_image(self, pixmap: QPixmap | None) -> None:
        self._source = pixmap
        self._rescale()

    def clear_image(self) -> None:
        self._source = None
        self.setPixmap(QPixmap())
        self.setText("")

    def show_message(self, text: str) -> None:
        """清掉图片并显示提示文字（QLabel 有 pixmap 时不会显示 text）。"""
        self._source = None
        self.setPixmap(QPixmap())
        self.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._source is None or self._source.isNull():
            return
        avail_w = max(40, self.width() - self._padding * 2)
        avail_h = max(40, self.height() - self._padding * 2)
        scaled = self._source.scaled(avail_w, avail_h, Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation)
        self.setPixmap(scaled)
