"""Small reusable UI building blocks."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.errors import AppError
from ui.theme import COLORS


def page_header(title: str, description: str, badge: str | None = None) -> QWidget:
    widget = QWidget()
    layout = QHBoxLayout(widget)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(14)
    text_layout = QVBoxLayout()
    text_layout.setSpacing(3)
    title_label = QLabel(title)
    title_label.setObjectName("pageTitle")
    description_label = QLabel(description)
    description_label.setObjectName("pageDescription")
    description_label.setWordWrap(True)
    text_layout.addWidget(title_label)
    text_layout.addWidget(description_label)
    layout.addLayout(text_layout, 1)
    if badge:
        pill = QLabel(badge)
        pill.setObjectName("pill")
        pill.setProperty("level", "info")
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(pill, 0, Qt.AlignmentFlag.AlignTop)
    return widget


def card(layout: QVBoxLayout | QHBoxLayout | None = None) -> QFrame:
    frame = QFrame()
    frame.setObjectName("card")
    if layout is None:
        inner = QVBoxLayout(frame)
        inner.setContentsMargins(16, 14, 16, 14)
        inner.setSpacing(10)
    return frame


def button(text: str, variant: str = "default") -> QPushButton:
    control = QPushButton(text)
    if variant != "default":
        control.setProperty("variant", variant)
    control.setCursor(Qt.CursorShape.PointingHandCursor)
    return control


def pill(text: str, level: str = "muted") -> QLabel:
    label = QLabel(text)
    label.setObjectName("pill")
    label.setProperty("level", level)
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def configure_table(headers: list[str], *, stretch_last: bool = True) -> QTableWidget:
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.verticalHeader().setVisible(False)
    table.setShowGrid(False)
    table.setAlternatingRowColors(True)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    table.horizontalHeader().setHighlightSections(False)
    table.horizontalHeader().setDefaultAlignment(
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
    )
    table.verticalHeader().setDefaultSectionSize(36)
    if stretch_last:
        table.horizontalHeader().setStretchLastSection(True)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    return table


def table_item(text: str, *, color: str | None = None, data=None) -> QTableWidgetItem:
    item = QTableWidgetItem(str(text))
    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    item.setToolTip(str(text))
    if color:
        item.setForeground(QBrush(QColor(color)))
    if data is not None:
        item.setData(Qt.ItemDataRole.UserRole, data)
    return item


def selected_id(table: QTableWidget) -> int | None:
    selected = table.selectionModel().selectedRows() if table.selectionModel() else []
    if not selected:
        return None
    item = table.item(selected[0].row(), 0)
    if item is None:
        return None
    value = item.data(Qt.ItemDataRole.UserRole)
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def status_color(label: str) -> str:
    if label in {"有效", "已确认", "进行中", "启用", "正常", "已修复"}:
        return COLORS["success"]
    if label in {"已过期", "已撤销", "失败", "拒绝", "严重", "高危"}:
        return COLORS["danger"]
    if label in {"待审核", "未生效", "已暂停", "即将到期", "待处理", "审核中", "接受风险"}:
        return COLORS["warning"]
    if label in {"误报"}:
        return COLORS["muted"]
    return COLORS["muted"]


def show_error(parent: QWidget, exc: Exception, title: str = "操作失败") -> None:
    if isinstance(exc, AppError):
        message = str(exc)
    else:
        message = f"{exc}\n\n详细信息已写入日志。"
    QMessageBox.warning(parent, title, message)


def confirm(
    parent: QWidget,
    title: str,
    message: str,
    *,
    dangerous: bool = False,
) -> bool:
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setIcon(QMessageBox.Icon.Warning if dangerous else QMessageBox.Icon.Question)
    box.setText(message)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(QMessageBox.StandardButton.No)
    return box.exec() == QMessageBox.StandardButton.Yes


def notice_frame(text: str, level: str = "info") -> QFrame:
    frame = QFrame()
    frame.setObjectName(
        "warningNotice" if level == "warning" else "dangerNotice" if level == "danger" else "notice"
    )
    layout = QHBoxLayout(frame)
    layout.setContentsMargins(12, 9, 12, 9)
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(
        "color: #fcd34d;"
        if level == "warning"
        else "color: #fca5a5;"
        if level == "danger"
        else "color: #bae6fd;"
    )
    layout.addWidget(label)
    return frame
