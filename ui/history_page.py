"""Audit log history page."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.timeutil import local_display
from ui.app_state import AppState
from ui.widgets import (
    button,
    configure_table,
    page_header,
    show_error,
    status_color,
    table_item,
)

_EVENT_LABELS = {
    "authorization_check": "授权检查",
    "authorization_change": "授权变更",
    "scope_asset_change": "资产变更",
    "project_change": "项目变更",
}
_DECISION_LABELS = {
    "allow": "允许",
    "deny": "拒绝",
    "info": "记录",
    "error": "错误",
}


class HistoryPage(QWidget):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)
        layout.addWidget(
            page_header(
                "历史记录",
                "项目、授权、资产变更和每一次后端授权检查的审计轨迹。",
                "仅追加审计",
            )
        )

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        filter_row.addWidget(QLabel("范围"))
        self._scope_combo = QComboBox()
        self._scope_combo.addItem("全部项目", None)
        self._scope_combo.addItem("当前项目", "current")
        self._scope_combo.currentIndexChanged.connect(self.refresh)
        filter_row.addWidget(self._scope_combo)
        self._refresh_button = button("刷新", "ghost")
        self._refresh_button.clicked.connect(self.refresh)
        filter_row.addWidget(self._refresh_button)
        filter_row.addStretch(1)
        self._summary = QLabel("")
        self._summary.setObjectName("muted")
        filter_row.addWidget(self._summary)
        layout.addLayout(filter_row)

        self._table = configure_table(
            ["时间", "项目", "事件", "目标", "操作", "结论", "说明"]
        )
        self._table.setMinimumHeight(320)
        layout.addWidget(self._table, 1)

        self._empty = QLabel("暂无审计记录。")
        self._empty.setObjectName("muted")
        layout.addWidget(self._empty)

        self._state.project_changed.connect(self.refresh)
        self._state.projects_changed.connect(self.refresh)

    def refresh(self) -> None:
        try:
            scope = self._scope_combo.currentData()
            project_id = self._state.current_project_id if scope == "current" else None
            logs = self._context.audit.list_logs(project_id, limit=500)
            projects = {
                project.project_id: project.project_name
                for project in self._context.project_service.list_projects()
            }
        except Exception as exc:
            show_error(self, exc, "读取审计记录失败")
            return

        self._table.setRowCount(0)
        for row_index, log in enumerate(logs):
            self._table.insertRow(row_index)
            project_name = (
                projects.get(log.project_id, f"#{log.project_id}") if log.project_id else "—"
            )
            values = [
                table_item(local_display(log.created_at, with_seconds=True)),
                table_item(project_name),
                table_item(_EVENT_LABELS.get(log.event_type, log.event_type)),
                table_item(log.target or "—"),
                table_item(log.operation or "—"),
                table_item(
                    _DECISION_LABELS.get(log.decision, log.decision),
                    color=status_color(_DECISION_LABELS.get(log.decision, log.decision)),
                ),
                table_item(log.message or "—"),
            ]
            for column, item in enumerate(values):
                self._table.setItem(row_index, column, item)
        self._table.resizeColumnsToContents()
        self._table.horizontalHeader().setStretchLastSection(True)
        self._summary.setText(f"显示最近 {len(logs)} 条 / 共 {self._context.audit.count()} 条")
        self._empty.setVisible(not logs)
