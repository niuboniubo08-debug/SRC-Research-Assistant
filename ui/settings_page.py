"""Read-only system information and security policy page."""

from __future__ import annotations

import platform
import sys

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from ui.widgets import button, page_header


class SettingsPage(QWidget):
    def __init__(self, context: AppContext) -> None:
        super().__init__()
        self._context = context
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)
        layout.addWidget(
            page_header(
                "系统设置",
                "本地运行环境、存储路径与不可绕过的安全策略。",
                "只读 · 当前版本",
            )
        )

        grid = QGridLayout()
        grid.setSpacing(16)
        grid.addWidget(
            self._information_card(
                "运行环境",
                [
                    ("Python", sys.version.split()[0]),
                    ("平台", platform.platform()),
                    ("数据库", self._context.database.health_check()[1]),
                    ("架构版本", f"v{self._context.database.schema_version()}"),
                ],
            ),
            0,
            0,
        )
        grid.addWidget(
            self._information_card(
                "存储位置",
                [
                    ("数据库", str(self._context.config.database_path)),
                    ("项目目录", str(self._context.config.projects_dir)),
                    ("证据目录", str(self._context.config.evidence_dir)),
                    ("审计日志", str(self._context.audit.audit_file)),
                ],
            ),
            0,
            1,
        )
        grid.addWidget(
            self._information_card(
                "强制安全策略",
                [
                    ("默认策略", "拒绝（deny by default）"),
                    ("远程范围", "精确匹配，不允许通配符"),
                    ("授权过期", "立即拒绝远程操作"),
                    ("重定向", "禁止自动跟随未授权目标"),
                    ("审计", "授权检查全部写入数据库与文件"),
                ],
            ),
            1,
            0,
        )
        grid.addWidget(
            self._information_card(
                "本阶段说明",
                [
                    ("完成", "项目 / 授权 / 资产 / 源码审计 / 依赖审计 / 漏洞与证据管理"),
                    ("未开发", "远程配置检查 / 报告导出"),
                    ("当前模式", "本地优先，不发起任何远程探测"),
                    ("版本", self._context.config.version),
                ],
            ),
            1,
            1,
        )
        layout.addLayout(grid)

        actions = QHBoxLayout()
        open_data = button("打开数据目录")
        open_data.clicked.connect(self._open_data_directory)
        actions.addWidget(open_data)
        open_logs = button("打开审计日志", "ghost")
        open_logs.clicked.connect(
            lambda: QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self._context.audit.audit_file.parent))
            )
        )
        actions.addWidget(open_logs)
        actions.addStretch(1)
        layout.addLayout(actions)
        layout.addStretch(1)

    def _information_card(self, title: str, rows: list[tuple[str, str]]) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)
        heading = QLabel(title)
        heading.setObjectName("sectionTitle")
        card_layout.addWidget(heading)
        for label, value in rows:
            row = QHBoxLayout()
            key = QLabel(label)
            key.setObjectName("muted")
            key.setMinimumWidth(76)
            row.addWidget(key, 0)
            text = QLabel(value)
            text.setWordWrap(True)
            text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            row.addWidget(text, 1)
            card_layout.addLayout(row)
        return card

    def _open_data_directory(self) -> None:
        QDesktopServices.openUrl(
            QUrl.fromLocalFile(str(self._context.config.storage_root))
        )
