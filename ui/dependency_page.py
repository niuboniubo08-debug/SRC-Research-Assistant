"""Dependency vulnerability audit page powered by pip-audit."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.errors import AppError, ConflictError
from core.models import Finding, ScanTask, ScanTaskStatus
from core.timeutil import local_display
from services.dependency_audit_service import (
    DependencyAuditOutcome,
    DependencyAuditService,
    DependencyDiscovery,
    DependencyScannerInfo,
)
from ui.app_state import AppState
from ui.widgets import (
    button,
    configure_table,
    confirm,
    page_header,
    selected_id,
    show_error,
    status_color,
    table_item,
)


class DependencyAuditWorker(QThread):
    progress = Signal(int, str, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: DependencyAuditService,
        project_id: int,
        dependency_path: str,
        timeout_seconds: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._project_id = project_id
        self._dependency_path = dependency_path
        self._timeout_seconds = timeout_seconds
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            outcome = self._service.run_audit(
                self._project_id,
                self._dependency_path,
                timeout_seconds=float(self._timeout_seconds),
                cancel_event=self.cancel_event,
                progress_callback=self._on_progress,
            )
        except Exception as exc:  # noqa: BLE001 - delivered through Qt signal
            self.failed.emit(str(exc))
            return
        self.completed.emit(outcome)

    def _on_progress(self, percent: int, message: str, scanner_name: str) -> None:
        self.progress.emit(percent, message, scanner_name)

    def request_cancel(self) -> None:
        self.cancel_event.set()


class DependencyPage(QWidget):
    scanning_changed = Signal(bool)

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._service = context.dependency_service
        self._worker: DependencyAuditWorker | None = None
        self._busy = False
        self._task: ScanTask | None = None
        self._discovery: DependencyDiscovery | None = None
        self._scanner_info: DependencyScannerInfo | None = None
        self._findings: list[Finding] = []
        self._findings_by_id: dict[int, Finding] = {}
        self._current_task_id: int | None = None
        self._scan_project_id: int | None = None
        self._build_ui()
        self._state.project_changed.connect(self._on_project_changed)
        self.refresh_all()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.addWidget(
            page_header(
                "依赖漏洞检查",
                "识别当前项目根目录的 Python 依赖文件，并通过 pip-audit 查询公开漏洞数据。",
                "第四阶段 · 本地依赖审计",
            ),
            1,
        )
        self.refresh_button = button("刷新")
        self.refresh_button.clicked.connect(self.refresh_all)
        header_row.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)
        layout.addWidget(self._build_project_card())
        layout.addWidget(self._build_control_card())
        layout.addLayout(self._build_results_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.findings_table = configure_table(
            ["风险", "依赖", "当前版本", "漏洞编号", "修复建议", "工具"]
        )
        self.findings_table.itemSelectionChanged.connect(self._show_selected_finding)
        splitter.addWidget(self.findings_table)
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([720, 360])
        layout.addWidget(splitter, 1)

        self.empty_label = QLabel("暂无依赖审计结果。")
        self.empty_label.setObjectName("muted")
        layout.addWidget(self.empty_label)

    def _build_project_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 13, 16, 13)
        layout.setSpacing(7)

        row = QHBoxLayout()
        title = QLabel("当前项目")
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        self.project_name_label = QLabel("—")
        self.project_name_label.setStyleSheet("font-weight: 600; color: #e7eef9;")
        row.addWidget(self.project_name_label)
        row.addSpacing(16)
        path_label = QLabel("本地路径")
        path_label.setObjectName("muted")
        row.addWidget(path_label)
        self.path_value = QLabel("—")
        self.path_value.setObjectName("muted")
        self.path_value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.path_value.setWordWrap(True)
        row.addWidget(self.path_value, 1)
        self.path_pill = QLabel("未选择")
        self.path_pill.setObjectName("pill")
        self.path_pill.setProperty("level", "muted")
        row.addWidget(self.path_pill)
        self.validate_button = button("重新校验", "ghost")
        self.validate_button.clicked.connect(self.refresh_all)
        row.addWidget(self.validate_button)
        self.register_button = button("登记为本地资产", "primary")
        self.register_button.clicked.connect(self._register_local_asset)
        self.register_button.hide()
        row.addWidget(self.register_button)
        layout.addLayout(row)

        info_row = QHBoxLayout()
        info_row.addWidget(self._label("依赖文件"))
        self.dependency_files_label = QLabel("—")
        self.dependency_files_label.setWordWrap(True)
        info_row.addWidget(self.dependency_files_label, 1)
        layout.addLayout(info_row)
        self.path_reason = QLabel("请选择当前项目。")
        self.path_reason.setObjectName("muted")
        self.path_reason.setWordWrap(True)
        layout.addWidget(self.path_reason)
        return card

    def _build_control_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(12)
        title = QLabel("依赖审计")
        title.setObjectName("sectionTitle")
        top.addWidget(title)
        self.scanner_label = QLabel("pip-audit 检查中…")
        self.scanner_label.setWordWrap(False)
        top.addWidget(self.scanner_label)
        top.addStretch(1)
        dep_label = QLabel("依赖文件")
        dep_label.setObjectName("muted")
        top.addWidget(dep_label)
        self.dependency_selector = QComboBox()
        self.dependency_selector.setMinimumWidth(210)
        self.dependency_selector.currentIndexChanged.connect(self._update_controls)
        top.addWidget(self.dependency_selector)
        timeout_label = QLabel("超时")
        timeout_label.setObjectName("muted")
        top.addWidget(timeout_label)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 900)
        self.timeout_spin.setValue(180)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setFixedWidth(94)
        top.addWidget(self.timeout_spin)
        self.start_button = button("开始审计", "primary")
        self.start_button.clicked.connect(self._start_audit)
        top.addWidget(self.start_button)
        self.cancel_button = button("取消审计", "danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_audit)
        top.addWidget(self.cancel_button)
        layout.addLayout(top)

        self.availability_note = QLabel("")
        self.availability_note.setObjectName("muted")
        self.availability_note.setWordWrap(True)
        layout.addWidget(self.availability_note)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.status_pill = QLabel("空闲")
        self.status_pill.setObjectName("pill")
        self.status_pill.setProperty("level", "muted")
        progress_row.addWidget(self.status_pill)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_row.addWidget(self.progress_bar, 1)
        self.current_step_label = QLabel("当前步骤：—")
        self.current_step_label.setObjectName("muted")
        progress_row.addWidget(self.current_step_label)
        layout.addLayout(progress_row)

        self.task_summary = QLabel("尚未运行依赖审计。")
        self.task_summary.setObjectName("muted")
        self.task_summary.setWordWrap(True)
        layout.addWidget(self.task_summary)
        self.task_meta = QLabel("")
        self.task_meta.setObjectName("muted")
        layout.addWidget(self.task_meta)
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "color: #fca5a5; background: #2d1417; border: 1px solid #6e2a30;"
            "border-radius: 6px; padding: 7px;"
        )
        self.error_label.hide()
        layout.addWidget(self.error_label)
        return card

    def _build_results_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title = QLabel("依赖漏洞结果")
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        row.addStretch(1)
        self.count_label = QLabel("0 个结果")
        self.count_label.setObjectName("muted")
        row.addWidget(self.count_label)
        return row

    def _build_detail_panel(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 13, 15, 13)
        layout.setSpacing(7)
        title = QLabel("结果详情")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.detail_title = QLabel("选择一条结果查看详情")
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet("font-weight: 600; color: #e7eef9;")
        layout.addWidget(self.detail_title)
        self.detail_meta = QLabel("")
        self.detail_meta.setObjectName("muted")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.detail_meta)
        layout.addWidget(self._label("漏洞说明"))
        self.detail_description = QPlainTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMinimumHeight(110)
        layout.addWidget(self.detail_description, 1)
        layout.addWidget(self._label("修复建议"))
        self.detail_recommendation = QPlainTextEdit()
        self.detail_recommendation.setReadOnly(True)
        self.detail_recommendation.setMinimumHeight(85)
        layout.addWidget(self.detail_recommendation, 1)
        return card

    @staticmethod
    def _label(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("muted")
        return label

    # ------------------------------------------------------------------ refresh
    def _current_project(self):
        return self._state.current_project

    def refresh_all(self) -> None:
        self._refresh_project_and_dependencies()
        self._refresh_scanner()
        if not self._busy:
            self._load_latest_task()
        self._update_controls()

    def _on_project_changed(self, _project) -> None:
        if not self._busy:
            self.refresh_all()

    def _refresh_project_and_dependencies(self) -> None:
        project = self._current_project()
        self.dependency_selector.blockSignals(True)
        self.dependency_selector.clear()
        self.dependency_selector.blockSignals(False)
        self.register_button.hide()
        if project is None:
            self.project_name_label.setText("未选择活动项目")
            self.path_value.setText("—")
            self.path_pill.setText("未选择")
            self.path_pill.setProperty("level", "muted")
            self.path_reason.setText("请先在项目管理中设置当前项目。")
            self.dependency_files_label.setText("—")
            self._discovery = None
            self._set_pill_style()
            self._update_controls()
            return
        self.project_name_label.setText(f"#{project.project_id}  {project.project_name}")
        self.path_value.setText(project.local_path or "未配置本地路径")
        if not project.local_path.strip():
            self.path_pill.setText("未配置路径")
            self.path_pill.setProperty("level", "warning")
            self.path_reason.setText("当前项目没有本地代码路径。")
            self.dependency_files_label.setText("—")
            self._discovery = None
            self._set_pill_style()
            self._update_controls()
            return
        try:
            decision = self._context.scope_validator.check_local_path(
                project.project_id, project.local_path, operation="dependency_audit"
            )
        except Exception as exc:
            self._discovery = None
            self.path_pill.setText("校验异常")
            self.path_pill.setProperty("level", "danger")
            self.path_reason.setText(f"路径校验异常：{exc}")
            self.dependency_files_label.setText("—")
            self._set_pill_style()
            self._update_controls()
            return
        if not decision.allowed:
            self._discovery = None
            self.path_pill.setText("未通过")
            self.path_pill.setProperty("level", "danger")
            self.path_reason.setText(f"路径未通过：{decision.reason}（{decision.code}）")
            self.dependency_files_label.setText("—")
            can_register = (
                decision.code == "local_target_not_in_scope"
                and Path(project.local_path).is_dir()
            )
            self.register_button.setVisible(can_register)
            self._set_pill_style()
            self._update_controls()
            return
        try:
            discovery = self._service.discover(project.project_id)
        except AppError as exc:
            self._discovery = None
            self.path_pill.setText("未通过")
            self.path_pill.setProperty("level", "danger")
            self.path_reason.setText(str(exc))
            self.dependency_files_label.setText("—")
            self._set_pill_style()
            self._update_controls()
            return
        except Exception as exc:
            self._discovery = None
            self.path_pill.setText("校验异常")
            self.path_pill.setProperty("level", "danger")
            self.path_reason.setText(f"依赖识别异常：{exc}")
            self.dependency_files_label.setText("—")
            self._set_pill_style()
            self._update_controls()
            return
        self._discovery = discovery
        self.path_pill.setText("已授权")
        self.path_pill.setProperty("level", "success")
        self._set_pill_style()
        self.path_reason.setText(
            f"路径校验通过，依赖文件搜索范围：{discovery.root}"
        )
        file_texts = []
        for item in discovery.files:
            if not item.supported:
                file_texts.append(f"{item.relative_path}（不可用：{item.reason}）")
            else:
                file_texts.append(f"{item.relative_path}（{item.dependency_count} 项）")
        self.dependency_files_label.setText(
            "；".join(file_texts) if file_texts else "未发现 requirements.txt 或 pyproject.toml"
        )
        if discovery.primary is None:
            self.path_reason.setText(discovery.message)
            self.register_button.hide()
        else:
            self.dependency_selector.blockSignals(True)
            for item in discovery.files:
                if item.supported:
                    self.dependency_selector.addItem(
                        f"{item.relative_path}  ({item.dependency_count} 项依赖)",
                        str(item.path),
                    )
            self.dependency_selector.blockSignals(False)
            index = self.dependency_selector.findData(str(discovery.primary.path))
            if index < 0:
                index = next(
                    (
                        i
                        for i in range(self.dependency_selector.count())
                        if Path(self.dependency_selector.itemData(i)).resolve(strict=False)
                        == discovery.primary.path.resolve(strict=False)
                    ),
                    0,
                )
            self.dependency_selector.setCurrentIndex(index)
            self.register_button.hide()
        self._update_controls()

    def _refresh_scanner(self) -> None:
        try:
            info = self._service.scanner_info()
        except Exception as exc:
            self.scanner_label.setText(f"pip-audit 状态检查失败：{exc}")
            self.availability_note.setText("")
            self._scanner_info = None
            return
        self._scanner_info = info
        if info.available:
            self.scanner_label.setText(f"pip-audit {info.version}  ·  可用")
            self.scanner_label.setStyleSheet(f"color: {status_color('正常')};")
            self.availability_note.setText("")
            self.availability_note.hide()
        else:
            self.scanner_label.setText(f"pip-audit {info.version}  ·  不可用".strip())
            self.scanner_label.setStyleSheet(f"color: {status_color('拒绝')};")
            self.availability_note.setText(f"不可用原因：{info.reason}")
            self.availability_note.show()

    def _load_latest_task(self) -> None:
        project = self._current_project()
        if project is None:
            self._task = None
            self._current_task_id = None
            self._findings = []
            self._findings_by_id = {}
            self.findings_table.setRowCount(0)
            self._update_task_display()
            return
        try:
            task = self._service.latest_task(project.project_id)
        except Exception as exc:
            show_error(self, exc, "读取依赖审计任务失败")
            return
        self._task = task
        self._current_task_id = task.task_id if task else None
        self._update_task_display()
        self._refresh_findings()

    def _update_task_display(self) -> None:
        task = self._task
        if task is None:
            self.status_pill.setText("空闲")
            self.status_pill.setProperty("level", "muted")
            self.progress_bar.setValue(0)
            self.current_step_label.setText("当前步骤：—")
            self.task_summary.setText("尚未运行依赖审计。")
            self.task_meta.setText("")
            self.error_label.hide()
            self._set_pill_style()
            return
        level = {
            ScanTaskStatus.PENDING: "muted",
            ScanTaskStatus.RUNNING: "info",
            ScanTaskStatus.COMPLETED: "success",
            ScanTaskStatus.FAILED: "danger",
            ScanTaskStatus.CANCELLED: "warning",
            ScanTaskStatus.BLOCKED: "warning",
        }[task.status]
        self.status_pill.setText(task.status_label)
        self.status_pill.setProperty("level", level)
        self.progress_bar.setValue(task.progress)
        self.current_step_label.setText(f"当前步骤：{task.current_scanner or '—'}")
        self.task_summary.setText(task.result_summary or "任务已创建。")
        finished = (
            local_display(task.finished_at, with_seconds=True) if task.finished_at else "—"
        )
        self.task_meta.setText(f"任务 #{task.task_id} · 完成时间：{finished}")
        if task.error_message:
            self.error_label.setText(task.error_message)
            self.error_label.show()
        else:
            self.error_label.hide()
        self._set_pill_style()

    def _set_pill_style(self) -> None:
        self.path_pill.style().unpolish(self.path_pill)
        self.path_pill.style().polish(self.path_pill)
        self.status_pill.style().unpolish(self.status_pill)
        self.status_pill.style().polish(self.status_pill)

    def _selected_dependency_path(self) -> str | None:
        data = self.dependency_selector.currentData()
        return str(data) if data else None

    def _update_controls(self) -> None:
        project = self._current_project()
        deps_ok = bool(
            self._discovery
            and self._discovery.primary is not None
            and self.dependency_selector.count() > 0
        )
        scanner_ok = bool(self._scanner_info and self._scanner_info.available)
        self.start_button.setEnabled(
            not self._busy and project is not None and deps_ok and scanner_ok
        )
        self.cancel_button.setEnabled(self._busy)
        self.timeout_spin.setEnabled(not self._busy)
        self.dependency_selector.setEnabled(
            not self._busy and self.dependency_selector.count() > 0
        )
        self.refresh_button.setEnabled(not self._busy)
        self.validate_button.setEnabled(not self._busy and project is not None)
        if self._discovery and self._discovery.primary is None:
            self.empty_label.setText(self._discovery.message)
        elif self.findings_table.rowCount() == 0:
            self.empty_label.setText("暂无依赖审计结果。")

    # ------------------------------------------------------------------ audit
    def _start_audit(self) -> None:
        if self._busy:
            return
        project = self._current_project()
        if project is None:
            return
        self.refresh_all()
        selected = self._selected_dependency_path()
        if not selected or not self._scanner_info or not self._scanner_info.available:
            self.error_label.setText("依赖文件或 pip-audit 不可用，无法开始审计。")
            self.error_label.show()
            return
        self._scan_project_id = project.project_id
        self._set_busy(True)
        self.error_label.hide()
        self.status_pill.setText("等待中")
        self.status_pill.setProperty("level", "info")
        self._set_pill_style()
        self.task_summary.setText("依赖审计任务启动中…")
        self.progress_bar.setValue(0)
        self.current_step_label.setText("当前步骤：准备")
        worker = DependencyAuditWorker(
            self._service,
            project.project_id,
            selected,
            self.timeout_spin.value(),
            self,
        )
        worker.progress.connect(self._on_progress)
        worker.completed.connect(self._on_completed)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.scanning_changed.emit(busy)
        self._update_controls()

    def _cancel_audit(self) -> None:
        if self._worker is None or not self._busy:
            return
        self._worker.request_cancel()
        self.cancel_button.setEnabled(False)
        self.status_pill.setText("取消中…")
        self.status_pill.setProperty("level", "warning")
        self._set_pill_style()
        self.task_summary.setText("正在请求取消依赖审计…")

    def _on_progress(self, percent: int, message: str, scanner_name: str) -> None:
        self.progress_bar.setValue(percent)
        self.task_summary.setText(message)
        self.current_step_label.setText(f"当前步骤：{scanner_name or message}")
        if not (self._worker is not None and self._worker.cancel_event.is_set()):
            self.status_pill.setText("审计中")
            self.status_pill.setProperty("level", "info")
            self._set_pill_style()

    def _on_completed(self, outcome: DependencyAuditOutcome) -> None:
        self._task = outcome.task
        self._current_task_id = outcome.task.task_id
        self._update_task_display()
        self._refresh_findings()
        if outcome.warnings:
            self.error_label.setText("\n".join(outcome.warnings[:10]))
            self.error_label.show()

    def _on_failed(self, message: str) -> None:
        self._load_latest_task()
        self.error_label.setText(message)
        self.error_label.show()
        self.status_pill.setText("失败")
        self.status_pill.setProperty("level", "danger")
        self._set_pill_style()
        self.task_summary.setText("依赖审计任务异常终止。")

    def _on_worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_busy(False)
        self._refresh_scanner()
        self._update_controls()
        if (
            self._scan_project_id is not None
            and self._current_project() is not None
            and self._current_project().project_id != self._scan_project_id
        ):
            self.refresh_all()
        self._scan_project_id = None

    # ------------------------------------------------------------------ results
    def _refresh_findings(self) -> None:
        project = self._current_project()
        if project is None or self._current_task_id is None:
            self._findings = []
            self._findings_by_id = {}
            self.findings_table.setRowCount(0)
            self.count_label.setText("0 个结果")
            self._clear_detail()
            return
        try:
            findings = self._service.list_findings(
                project.project_id, task_id=self._current_task_id
            )
        except Exception as exc:
            show_error(self, exc, "读取依赖漏洞结果失败")
            return
        selected = selected_id(self.findings_table)
        self._findings = findings
        self._findings_by_id = {
            finding.finding_id: finding
            for finding in findings
            if finding.finding_id is not None
        }
        self.findings_table.setRowCount(0)
        for row_index, finding in enumerate(findings):
            self.findings_table.insertRow(row_index)
            dependency = str(finding.metadata.get("dependency_name") or "—")
            version = str(finding.metadata.get("current_version") or "—")
            values = [
                table_item(
                    finding.severity_label,
                    color=status_color(finding.severity_label),
                ),
                table_item(dependency),
                table_item(version),
                table_item(finding.rule_id),
                table_item(finding.recommendation or "—"),
                table_item(finding.scanner_label),
            ]
            if finding.finding_id is not None:
                values[0].setData(Qt.ItemDataRole.UserRole, finding.finding_id)
            for column, item in enumerate(values):
                self.findings_table.setItem(row_index, column, item)
        header = self.findings_table.horizontalHeader()
        header.setStretchLastSection(False)
        for column, width in enumerate([56, 105, 82, 138, 120, 82]):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.findings_table.setColumnWidth(column, width)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.count_label.setText(f"{len(findings)} 个结果")
        self.empty_label.setText(
            "当前任务未发现已知依赖漏洞。"
            if self._task and self._task.status is ScanTaskStatus.COMPLETED and not findings
            else "暂无依赖审计结果。"
        )
        self.empty_label.setVisible(not findings)
        target_row = -1
        for row_index, finding in enumerate(findings):
            if finding.finding_id == selected:
                target_row = row_index
                break
        if target_row >= 0:
            self.findings_table.selectRow(target_row)
        elif findings:
            self.findings_table.selectRow(0)
        else:
            self._clear_detail()

    def _show_selected_finding(self) -> None:
        finding_id = selected_id(self.findings_table)
        if finding_id is None:
            self._clear_detail()
            return
        finding = self._findings_by_id.get(finding_id)
        if finding is None:
            self._clear_detail()
            return
        metadata = finding.metadata
        dependency = str(metadata.get("dependency_name") or "—")
        version = str(metadata.get("current_version") or "—")
        aliases = metadata.get("aliases") or []
        alias_text = "、".join(str(alias) for alias in aliases) if aliases else "—"
        self.detail_title.setText(finding.title)
        self.detail_meta.setText(
            f"依赖：{dependency} {version}  ·  漏洞编号：{finding.rule_id}  ·  "
            f"别名：{alias_text}\n"
            f"来源：{metadata.get('source', 'pip-audit/PyPI')}  ·  "
            f"受影响版本：{metadata.get('affected_versions', '—')}"
        )
        self.detail_description.setPlainText(finding.description or "—")
        self.detail_recommendation.setPlainText(finding.recommendation or "—")

    def _clear_detail(self) -> None:
        self.detail_title.setText("暂无结果")
        self.detail_meta.setText("尚未选择依赖审计结果。")
        self.detail_description.setPlainText("")
        self.detail_recommendation.setPlainText("")

    # ------------------------------------------------------------------ actions
    def _register_local_asset(self) -> None:
        project = self._current_project()
        if project is None or not project.local_path.strip():
            return
        if not confirm(
            self,
            "登记本地资产",
            f"将以下目录登记为当前项目的本地源代码资产？\n\n{project.local_path}\n\n"
            "这是本地资产，不会授权任何远程目标。",
        ):
            return
        try:
            self._context.scope_service.create_asset(
                project.project_id,
                asset_type="local_project",
                asset_value=project.local_path,
                notes="依赖漏洞检查页面登记",
            )
        except ConflictError:
            pass
        except Exception as exc:
            show_error(self, exc, "登记本地资产失败")
            return
        self.refresh_all()

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            if not self._worker.wait(15000):
                self._worker.wait(5000)
