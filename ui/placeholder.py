"""Explicit, non-deceptive placeholder for modules outside this phase."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

from ui.widgets import page_header


class PlaceholderPage(QWidget):
    def __init__(
        self,
        title: str,
        description: str,
        planned_features: list[str],
        *,
        security_note: str,
    ) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(page_header(title, description, "未开发 · 第二阶段范围外"))

        panel = QFrame()
        panel.setObjectName("card")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        panel_layout.setSpacing(12)

        status = QLabel("本页面尚未实现")
        status.setObjectName("sectionTitle")
        status.setStyleSheet("color: #fbbf24;")
        panel_layout.addWidget(status)
        explanation = QLabel(
            "这是明确的占位页面，不会显示虚构的检测结果或伪造的完成状态。"
            "本阶段只实现项目管理、授权管理、授权资产与后端安全控制。"
        )
        explanation.setWordWrap(True)
        explanation.setObjectName("muted")
        panel_layout.addWidget(explanation)

        planned = QLabel("计划功能")
        planned.setObjectName("sectionTitle")
        planned.setStyleSheet("margin-top: 8px;")
        panel_layout.addWidget(planned)
        for feature in planned_features:
            row = QLabel(f"·  {feature}")
            row.setWordWrap(True)
            row.setStyleSheet("color: #a9b9cc; padding: 2px 0;")
            panel_layout.addWidget(row)

        safety = QLabel(f"安全边界：{security_note}")
        safety.setWordWrap(True)
        safety.setStyleSheet(
            "color: #7dd3fc; background: #10283a; border: 1px solid #1d4f68;"
            "border-radius: 8px; padding: 10px; margin-top: 8px;"
        )
        panel_layout.addWidget(safety)
        panel_layout.addStretch(1)
        layout.addWidget(panel, 1)

        footer = QLabel("后续阶段完成并通过测试后，本页将替换为实际功能。")
        footer.setObjectName("muted")
        footer.setAlignment(Qt.AlignmentFlag.AlignRight)
        layout.addWidget(footer)
