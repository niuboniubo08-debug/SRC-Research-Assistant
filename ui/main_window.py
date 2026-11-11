"""Main application window with fixed navigation and page stack."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from ui.app_state import AppState
from ui.config_audit_page import ConfigAuditPage
from ui.dashboard import DashboardPage
from ui.dependency_page import DependencyPage
from ui.evidence_page import EvidencePage
from ui.history_page import HistoryPage
from ui.project_page import ProjectPage
from ui.report_page import ReportPage
from ui.settings_page import SettingsPage
from ui.source_audit_page import SourceAuditPage
from ui.vulnerability_page import VulnerabilityPage
from ui.widgets import show_error


class MainWindow(QMainWindow):
    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._syncing_project_combo = False
        self._active_scans: set[str] = set()
        self.nav_buttons: dict[str, QPushButton] = {}
        self.pages_by_key: dict[str, QWidget] = {}

        self.setWindowTitle(f"{context.config.name} · {context.config.version}")
        self.resize(context.config.window_width, context.config.window_height)
        self.setMinimumSize(1180, 720)
        self._build_ui()
        self._connect_state()
        self._refresh_project_combo()
        self.navigate("dashboard")

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("appRoot")
        self.setCentralWidget(root)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        root_layout.addWidget(self._build_sidebar())

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addWidget(self._build_header())

        self.stack = QStackedWidget()
        self._add_pages()
        content_layout.addWidget(self.stack, 1)
        root_layout.addWidget(content, 1)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(246)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(14, 18, 14, 14)
        layout.setSpacing(5)

        brand = QHBoxLayout()
        brand.setSpacing(10)
        mark = QLabel("SRC")
        mark.setObjectName("brandMark")
        mark.setFixedSize(48, 44)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(1)
        name = QLabel("Research Assistant")
        name.setObjectName("brandName")
        caption = QLabel("AUTHORIZED SECURITY")
        caption.setObjectName("brandCaption")
        brand_text.addWidget(name)
        brand_text.addWidget(caption)
        brand.addLayout(brand_text)
        layout.addLayout(brand)
        layout.addSpacing(18)

        section = QLabel("工作台")
        section.setObjectName("brandCaption")
        section.setContentsMargins(10, 0, 0, 3)
        layout.addWidget(section)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        navigation = [
            ("dashboard", "总览"),
            ("projects", "项目管理"),
            ("source_audit", "源代码审计"),
            ("dependencies", "依赖漏洞检查"),
            ("config_audit", "安全配置检查"),
            ("vulnerabilities", "漏洞管理"),
            ("evidence", "证据中心"),
            ("reports", "报告中心"),
            ("history", "历史记录"),
            ("settings", "系统设置"),
        ]
        for index, (key, label) in enumerate(navigation, start=1):
            nav = QPushButton(f"{index:02d}    {label}")
            nav.setObjectName("navButton")
            nav.setCheckable(True)
            nav.setCursor(Qt.CursorShape.PointingHandCursor)
            nav.clicked.connect(lambda _checked=False, page_key=key: self.navigate(page_key))
            self._nav_group.addButton(nav)
            self.nav_buttons[key] = nav
            layout.addWidget(nav)
            if key == "projects":
                layout.addSpacing(4)
            if key == "config_audit":
                layout.addSpacing(4)

        layout.addStretch(1)
        divider = QFrame()
        divider.setFixedHeight(1)
        divider.setStyleSheet("background: #1c2a40;")
        layout.addWidget(divider)
        footer = QLabel(f"v{self._context.config.version}  ·  PHASE 6")
        footer.setObjectName("brandCaption")
        footer.setContentsMargins(8, 5, 0, 0)
        layout.addWidget(footer)
        local_only = QLabel("LOCAL FIRST  /  NO AUTO EXPLOIT")
        local_only.setObjectName("brandCaption")
        local_only.setContentsMargins(8, 0, 0, 4)
        layout.addWidget(local_only)
        return sidebar

    def _build_header(self) -> QWidget:
        header = QWidget()
        header.setObjectName("headerBar")
        header.setFixedHeight(72)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(24, 10, 24, 10)
        layout.setSpacing(18)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(1)
        title = QLabel("SRC Research Assistant")
        title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #f1f5f9;")
        subtitle = QLabel("授权范围内的软件安全研究工作台")
        subtitle.setObjectName("pageDescription")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        layout.addLayout(title_layout)
        layout.addStretch(1)

        project_label = QLabel("当前项目")
        project_label.setObjectName("muted")
        layout.addWidget(project_label)
        self.project_combo = QComboBox()
        self.project_combo.setMinimumWidth(290)
        self.project_combo.setToolTip("切换当前活动项目；切换不会改变授权状态")
        self.project_combo.currentIndexChanged.connect(self._project_combo_changed)
        layout.addWidget(self.project_combo)

        self.system_status = QLabel("")
        self.system_status.setObjectName("pill")
        self.system_status.setProperty("level", "success")
        self.system_status.setToolTip("数据库连接与安全控制状态")
        layout.addWidget(self.system_status)
        self._update_system_status()
        return header

    def _add_pages(self) -> None:
        dashboard = DashboardPage(self._context, self._state)
        projects = ProjectPage(self._context, self._state)
        history = HistoryPage(self._context, self._state)
        pages = {
            "dashboard": dashboard,
            "projects": projects,
            "source_audit": SourceAuditPage(self._context, self._state),
            "dependencies": DependencyPage(self._context, self._state),
            "config_audit": ConfigAuditPage(),
            "vulnerabilities": VulnerabilityPage(self._context, self._state),
            "evidence": EvidencePage(self._context, self._state),
            "reports": ReportPage(self._context, self._state),
            "history": history,
            "settings": SettingsPage(self._context),
        }
        self.dashboard_page = dashboard
        self.project_page = projects
        self.history_page = history
        self.source_audit_page = pages["source_audit"]
        self.dependency_page = pages["dependencies"]
        self.vulnerability_page = pages["vulnerabilities"]
        self.evidence_page = pages["evidence"]
        self.report_page = pages["reports"]
        for key, page in pages.items():
            self.pages_by_key[key] = page
            self.stack.addWidget(page)
        dashboard.navigate_requested.connect(self.navigate)
        projects.projects_changed.connect(self._refresh_project_combo)
        self.source_audit_page.scanning_changed.connect(
            lambda busy: self._set_scanning_busy("source_audit", busy)
        )
        self.dependency_page.scanning_changed.connect(
            lambda busy: self._set_scanning_busy("dependencies", busy)
        )
        self.vulnerability_page.open_evidence_requested.connect(
            self._open_evidence
        )
        self.evidence_page.open_vulnerability_requested.connect(
            self._open_vulnerability
        )

    # ------------------------------------------------------------------ state
    def _connect_state(self) -> None:
        self._state.project_changed.connect(lambda _project: self._refresh_project_combo())
        self._state.projects_changed.connect(self._refresh_project_combo)

    def _on_page_changed(self, key: str) -> None:
        if key == "dashboard":
            self.dashboard_page.refresh()
        elif key == "history":
            self.history_page.refresh()
        elif key == "projects":
            self.project_page.refresh_all()
        elif key == "source_audit":
            self.source_audit_page.refresh_all()
        elif key == "dependencies":
            self.dependency_page.refresh_all()
        elif key == "vulnerabilities":
            self.vulnerability_page.refresh()
        elif key == "evidence":
            self.evidence_page.refresh()
        elif key == "reports":
            self.report_page.refresh()

    def _refresh_project_combo(self) -> None:
        current_id = self._state.current_project_id
        try:
            projects = self._context.project_service.list_projects()
        except Exception as exc:
            show_error(self, exc, "读取当前项目失败")
            return
        self._syncing_project_combo = True
        try:
            self.project_combo.clear()
            self.project_combo.addItem("未选择活动项目", None)
            for project in projects:
                self.project_combo.addItem(
                    f"#{project.project_id}  {project.project_name}", project.project_id
                )
            index = self.project_combo.findData(current_id) if current_id is not None else 0
            self.project_combo.setCurrentIndex(max(0, index))
        finally:
            self._syncing_project_combo = False

    def _project_combo_changed(self) -> None:
        if self._syncing_project_combo:
            return
        project_id = self.project_combo.currentData()
        try:
            self._state.set_active_project(project_id)
        except Exception as exc:
            show_error(self, exc, "切换当前项目失败")
            self._refresh_project_combo()
            return
        current = self._state.current_project
        if current:
            self.setWindowTitle(f"{self._context.config.name} · {current.project_name}")
        else:
            self.setWindowTitle(f"{self._context.config.name} · {self._context.config.version}")

    def _update_system_status(self) -> None:
        healthy, message = self._context.database.health_check()
        if healthy:
            self.system_status.setText("●  本地运行 · 审计与证据管理已启用")
            self.system_status.setProperty("level", "success")
            self.system_status.setToolTip(message)
        else:
            self.system_status.setText("●  数据库异常")
            self.system_status.setProperty("level", "danger")
            self.system_status.setToolTip(message)

    def _set_scanning_busy(self, page_key: str, busy: bool) -> None:
        if busy:
            self._active_scans.add(page_key)
        else:
            self._active_scans.discard(page_key)
        is_busy = bool(self._active_scans)
        self.project_combo.setEnabled(not is_busy)
        self.project_combo.setToolTip(
            "扫描进行中，暂不能切换当前项目" if is_busy else "切换当前活动项目；切换不会改变授权状态"
        )

    def _open_evidence(
        self, project_id: int, finding_id: int, evidence_id: int
    ) -> None:
        self.navigate("evidence")
        self.evidence_page.select_evidence(project_id, finding_id, evidence_id)

    def _open_vulnerability(self, project_id: int, finding_id: int) -> None:
        self.navigate("vulnerabilities")
        self.vulnerability_page.select_finding(project_id, finding_id)

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        try:
            self.source_audit_page.shutdown()
            self.dependency_page.shutdown()
            self.vulnerability_page.shutdown()
            self.evidence_page.shutdown()
        finally:
            super().closeEvent(event)

    # ------------------------------------------------------------------ navigation
    def navigate(self, key: str) -> None:
        page = self.pages_by_key.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        button = self.nav_buttons.get(key)
        if button is not None:
            button.setChecked(True)
        self._on_page_changed(key)
