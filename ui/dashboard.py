"""Dashboard with live project and security posture summaries."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "总览",
                "本地优先的 SRC 授权研究工作台。所有安全控制都在服务层执行。",
                "第五阶段 · 漏洞与证据管理",
            ),
            1,
        )
        refresh_button = button("刷新")
        refresh_button.clicked.connect(self.refresh)
        header_row.addWidget(refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        self._context_label = QLabel("")
        self._context_label.setObjectName("muted")
        layout.addWidget(self._context_label)

        stats = QGridLayout()
        stats.setHorizontalSpacing(14)
        stats.setVerticalSpacing(14)
        self._project_value = self._stat_card(stats, 0, 0, "项目总数", "本地项目库")
        self._auth_value = self._stat_card(stats, 0, 1, "有效授权", "当前处于有效窗口")
        self._asset_value = self._stat_card(stats, 0, 2, "授权资产", "远程与本地分开管理")
        self._expiry_value = self._stat_card(stats, 0, 3, "7 日内到期", "已确认授权")
        layout.addLayout(stats)

        body = QHBoxLayout()
        body.setSpacing(16)

        recent_card = QFrame()
        recent_card.setObjectName("card")
        recent_layout = QVBoxLayout(recent_card)
        recent_layout.setContentsMargins(18, 16, 18, 16)
        recent_layout.setSpacing(12)
        recent_title = QLabel("最近项目")
        recent_title.setObjectName("sectionTitle")
        recent_layout.addWidget(recent_title)
        self._recent_table = configure_table(["项目", "类型", "状态", "创建时间"])
        self._recent_table.setMinimumHeight(220)
        recent_layout.addWidget(self._recent_table, 1)
        manage = button("管理项目", "primary")
        manage.clicked.connect(lambda: self.navigate_requested.emit("projects"))
        recent_layout.addWidget(manage, 0, Qt.AlignmentFlag.AlignLeft)
        body.addWidget(recent_card, 2)

        policy_card = QFrame()
        policy_card.setObjectName("card")
        policy_layout = QVBoxLayout(policy_card)
        policy_layout.setContentsMargins(18, 16, 18, 16)
        policy_layout.setSpacing(10)
        policy_title = QLabel("安全基线")
        policy_title.setObjectName("sectionTitle")
        policy_layout.addWidget(policy_title)
        policies = [
            ("默认策略", "拒绝未授权远程操作"),
            ("范围匹配", "精确域名 / IP，无通配符"),
            ("授权检查", "后端执行并写入审计日志"),
            ("重定向", "不自动跟随未授权目标"),
            ("远程探测", "当前阶段不发起"),
        ]
        for name, value in policies:
            row = QHBoxLayout()
            key = QLabel(name)
            key.setObjectName("muted")
            key.setMinimumWidth(76)
            row.addWidget(key)
            val = QLabel(value)
            val.setWordWrap(True)
            row.addWidget(val, 1)
            policy_layout.addLayout(row)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #22314c;")
        policy_layout.addWidget(divider)
        self._scope_hint = QLabel("")
        self._scope_hint.setWordWrap(True)
        self._scope_hint.setStyleSheet(
            "color: #7dd3fc; background: #10283a; border: 1px solid #1d4f68;"
            "border-radius: 8px; padding: 9px;"
        )
        policy_layout.addWidget(self._scope_hint)
        policy_layout.addStretch(1)
        body.addWidget(policy_card, 1)
        layout.addLayout(body, 1)

        self._state.project_changed.connect(self.refresh)
        self._state.projects_changed.connect(self.refresh)

    def _stat_card(self, grid: QGridLayout, row: int, column: int, label: str, hint: str) -> QLabel:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 13, 16, 13)
        card_layout.setSpacing(2)
        title = QLabel(label)
        title.setObjectName("statLabel")
        value = QLabel("0")
        value.setObjectName("statValue")
        detail = QLabel(hint)
        detail.setObjectName("statHint")
        card_layout.addWidget(title)
        card_layout.addWidget(value)
        card_layout.addWidget(detail)
        grid.addWidget(card, row, column)
        return value

    def refresh(self) -> None:
        try:
            projects = self._context.project_service.list_projects()
            current = self._state.current_project
            effective = self._context.authorization_service.count_effective(
                current.project_id if current else None
            )
            assets = self._context.scope_service.count_assets(
                current.project_id if current else None
            )
            expiring = self._context.authorization_service.count_expiring_soon(
                7, current.project_id if current else None
            )
        except Exception as exc:
            show_error(self, exc, "读取总览失败")
            return

        self._project_value.setText(str(len(projects)))
        self._auth_value.setText(str(effective))
        self._asset_value.setText(str(assets))
        self._expiry_value.setText(str(expiring))
        if current:
            self._context_label.setText(
                f"当前项目：#{current.project_id}  {current.project_name}  ·  {current.type_label}"
            )
            self._scope_hint.setText(
                f"当前项目范围：{effective} 条有效授权，{assets} 个授权资产。"
                "远程操作仍需通过逐次后端检查。"
            )
        else:
            self._context_label.setText("当前未选择活动项目。项目列表中的操作只影响所选项目。")
            self._scope_hint.setText("尚未选择活动项目。可前往项目管理设置当前项目。")

        self._recent_table.setRowCount(0)
        for row_index, project in enumerate(projects[:6]):
            self._recent_table.insertRow(row_index)
            current_mark = "  · 当前" if current and current.project_id == project.project_id else ""
            self._recent_table.setItem(
                row_index, 0, table_item(f"{project.project_name}{current_mark}", data=project.project_id)
            )
            self._recent_table.setItem(row_index, 1, table_item(project.type_label))
            self._recent_table.setItem(
                row_index,
                2,
                table_item(project.status_label, color=status_color(project.status_label)),
            )
            self._recent_table.setItem(
                row_index, 3, table_item(local_display(project.created_at))
            )
        self._recent_table.resizeColumnsToContents()
        self._recent_table.horizontalHeader().setStretchLastSection(True)
