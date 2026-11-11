"""Dark Windows desktop theme."""

from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

COLORS = {
    "bg": "#0a1120",
    "sidebar": "#0d1627",
    "panel": "#111b2d",
    "panel_alt": "#152238",
    "border": "#22314c",
    "border_strong": "#314563",
    "text": "#e7eef9",
    "muted": "#8a9bb3",
    "subtle": "#64748b",
    "accent": "#38bdf8",
    "accent_dark": "#0e7490",
    "success": "#34d399",
    "warning": "#fbbf24",
    "danger": "#f87171",
    "selection": "#17324d",
}

DARK_QSS = """
* {
    font-family: "Microsoft YaHei UI", "Segoe UI Variable", "Segoe UI";
    font-size: 10pt;
    color: #e7eef9;
}
QMainWindow, QDialog, QWidget#appRoot {
    background: #0a1120;
}
QWidget#sidebar {
    background: #0d1627;
    border-right: 1px solid #1c2a40;
}
QWidget#headerBar {
    background: #0d1627;
    border-bottom: 1px solid #1c2a40;
}
QLabel {
    background: transparent;
}
QLabel#brandMark {
    background: #12324a;
    color: #7dd3fc;
    border: 1px solid #1f5a78;
    border-radius: 10px;
    font-size: 14pt;
    font-weight: 700;
}
QLabel#brandName {
    color: #f1f5f9;
    font-size: 12pt;
    font-weight: 700;
}
QLabel#brandCaption, QLabel#muted, QLabel#formHint {
    color: #8294ad;
    font-size: 9pt;
}
QLabel#pageTitle {
    color: #f8fafc;
    font-size: 20pt;
    font-weight: 700;
}
QLabel#pageDescription {
    color: #8294ad;
    font-size: 9.5pt;
}
QLabel#sectionTitle {
    color: #dbe7f5;
    font-size: 11pt;
    font-weight: 600;
}
QLabel#statValue {
    color: #f8fafc;
    font-size: 25pt;
    font-weight: 700;
}
QLabel#statLabel {
    color: #8294ad;
    font-size: 9pt;
}
QLabel#statHint {
    color: #64748b;
    font-size: 8.5pt;
}
QLabel#pill {
    border-radius: 10px;
    padding: 4px 10px;
    font-size: 8.5pt;
    font-weight: 600;
}
QLabel#pill[level="success"] {
    color: #6ee7b7;
    background: #0b2f28;
    border: 1px solid #145648;
}
QLabel#pill[level="warning"] {
    color: #fcd34d;
    background: #33260a;
    border: 1px solid #6b4e0b;
}
QLabel#pill[level="danger"] {
    color: #fca5a5;
    background: #3a1518;
    border: 1px solid #742a2f;
}
QLabel#pill[level="info"] {
    color: #7dd3fc;
    background: #0d2a3d;
    border: 1px solid #164e63;
}
QLabel#pill[level="muted"] {
    color: #94a3b8;
    background: #182235;
    border: 1px solid #2a3a53;
}
QFrame#card {
    background: #111b2d;
    border: 1px solid #202e46;
    border-radius: 12px;
}
QFrame#notice {
    background: #10283a;
    border: 1px solid #1d4f68;
    border-radius: 10px;
}
QFrame#warningNotice {
    background: #2c210d;
    border: 1px solid #6b4e0b;
    border-radius: 10px;
}
QFrame#dangerNotice {
    background: #2d1417;
    border: 1px solid #6e2a30;
    border-radius: 10px;
}
QPushButton {
    background: #172337;
    border: 1px solid #2a3b55;
    border-radius: 7px;
    padding: 7px 14px;
    min-height: 18px;
    color: #dbe7f5;
}
QPushButton:hover {
    background: #1c2c44;
    border-color: #3b526f;
}
QPushButton:pressed {
    background: #101a2b;
}
QPushButton:disabled {
    color: #53637a;
    background: #111a29;
    border-color: #1b2738;
}
QPushButton[variant="primary"] {
    background: #0e7490;
    border-color: #0891b2;
    color: #f0fdff;
    font-weight: 600;
}
QPushButton[variant="primary"]:hover {
    background: #0891b2;
    border-color: #22d3ee;
}
QPushButton[variant="danger"] {
    background: #37161a;
    border-color: #6b2a31;
    color: #fca5a5;
}
QPushButton[variant="danger"]:hover {
    background: #4a1c22;
    border-color: #b33a45;
}
QPushButton[variant="ghost"] {
    background: transparent;
    border-color: transparent;
    color: #93c5fd;
    padding: 4px 6px;
}
QPushButton[variant="ghost"]:hover {
    background: #142239;
    border-color: #24364f;
}
QPushButton#navButton {
    background: transparent;
    border: 1px solid transparent;
    border-radius: 8px;
    padding: 10px 14px;
    text-align: left;
    color: #93a4bb;
    font-size: 10pt;
}
QPushButton#navButton:hover {
    background: #122036;
    color: #dbeafe;
}
QPushButton#navButton:checked {
    background: #122c42;
    border: 1px solid #1e4e69;
    color: #7dd3fc;
    font-weight: 600;
}
QLineEdit, QPlainTextEdit, QTextEdit, QComboBox, QDateTimeEdit, QSpinBox {
    background: #0c1525;
    border: 1px solid #293a53;
    border-radius: 6px;
    padding: 6px 9px;
    color: #e7eef9;
    selection-background-color: #155e75;
    min-height: 20px;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus,
QDateTimeEdit:focus, QSpinBox:focus {
    border-color: #0ea5e9;
}
QLineEdit:disabled, QComboBox:disabled, QDateTimeEdit:disabled {
    color: #56667d;
    background: #0f1725;
}
QLineEdit[readOnly="true"] {
    color: #a8b7ca;
    background: #101b2b;
}
QComboBox::drop-down {
    border: none;
    width: 24px;
}
QComboBox QAbstractItemView {
    background: #101b2c;
    border: 1px solid #2a3d58;
    selection-background-color: #173f55;
    outline: 0;
    padding: 3px;
}
QAbstractItemView {
    background: #0c1525;
    alternate-background-color: #101b2d;
    border: 1px solid #22314a;
    border-radius: 8px;
    selection-background-color: #173f55;
    selection-color: #f0f9ff;
    outline: 0;
}
QTableWidget {
    background: #0e1828;
    alternate-background-color: #111d2f;
    gridline-color: transparent;
    border: 1px solid #22314a;
    border-radius: 9px;
    selection-background-color: #173f55;
    selection-color: #f0f9ff;
}
QTableWidget::item {
    padding: 7px 8px;
    border-bottom: 1px solid #17243a;
}
QHeaderView::section {
    background: #131f32;
    color: #8fa3bb;
    border: none;
    border-bottom: 1px solid #26344d;
    padding: 8px;
    font-size: 8.5pt;
    font-weight: 600;
}
QTableCornerButton::section {
    background: #131f32;
}
QTabWidget::pane {
    border: 1px solid #202e46;
    border-radius: 10px;
    top: -1px;
    background: #0d1727;
}
QTabBar::tab {
    background: transparent;
    color: #8294ad;
    border: 1px solid transparent;
    border-bottom: 2px solid transparent;
    padding: 9px 18px;
    margin-right: 4px;
}
QTabBar::tab:hover {
    color: #cbd5e1;
}
QTabBar::tab:selected {
    color: #7dd3fc;
    border-bottom: 2px solid #0ea5e9;
    background: #101d30;
}
QProgressBar {
    background: #0c1525;
    border: 1px solid #293a53;
    border-radius: 5px;
    min-height: 15px;
    max-height: 15px;
    text-align: center;
    color: #cbd5e1;
    font-size: 8pt;
}
QProgressBar::chunk {
    background: #0e7490;
    border-radius: 4px;
}
QSplitter::handle {
    background: #1c2a40;
    width: 2px;
    height: 2px;
}
QPlainTextEdit[readOnly="true"] {
    background: #0b1422;
    border-color: #203048;
}
QScrollBar:vertical {
    background: #0c1525;
    width: 10px;
    margin: 2px;
}
QScrollBar::handle:vertical {
    background: #2b3d57;
    min-height: 28px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background: #3a506e;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background: #0c1525;
    height: 10px;
    margin: 2px;
}
QScrollBar::handle:horizontal {
    background: #2b3d57;
    min-width: 28px;
    border-radius: 4px;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
QGroupBox {
    border: 1px solid #202e46;
    border-radius: 9px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #b7c7db;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 12px;
    padding: 0 5px;
}
QDialog QLabel#dialogTitle {
    font-size: 15pt;
    font-weight: 700;
    color: #f8fafc;
}
QDialog QLabel#errorLabel {
    color: #fca5a5;
    background: #2d1417;
    border: 1px solid #6e2a30;
    border-radius: 6px;
    padding: 7px;
}
QMessageBox {
    background: #0e1828;
}
QToolTip {
    background: #162337;
    color: #e2e8f0;
    border: 1px solid #30435f;
    padding: 5px;
}
QCheckBox {
    spacing: 7px;
    color: #cbd5e1;
}
QCheckBox::indicator {
    width: 15px;
    height: 15px;
    border: 1px solid #3a4f6c;
    border-radius: 3px;
    background: #0c1525;
}
QCheckBox::indicator:checked {
    background: #0e7490;
    border-color: #22d3ee;
}
"""


def apply_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Base, QColor("#0c1525"))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor("#111d2f"))
    palette.setColor(QPalette.ColorRole.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Button, QColor("#172337"))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text"]))
    palette.setColor(QPalette.ColorRole.Highlight, QColor("#0e7490"))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#f0f9ff"))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor("#162337"))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS["text"]))
    app.setPalette(palette)
    font = QFont("Microsoft YaHei UI", 10)
    app.setFont(font)
    app.setStyleSheet(DARK_QSS)
