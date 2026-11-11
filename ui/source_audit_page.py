"""Source code audit page with local-only Bandit/Semgrep scanning."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
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
from core.models import Finding, ScanTask, ScanTaskStatus, Severity
from core.timeutil import local_display
from services.scan_service import ScanOutcome, ScanService
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


class ScanWorker(QThread):
    """Runs ScanService outside the UI thread."""

    progress = Signal(int, str, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service: ScanService,
        project_id: int,
        scanner_names: list[str],
        timeout_seconds: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._project_id = project_id
        self._scanner_names = scanner_names
        self._timeout_seconds = timeout_seconds
        self.cancel_event = threading.Event()

    def run(self) -> None:
        try:
            outcome = self._service.run_scan(
                self._project_id,
                self._scanner_names,
                timeout_seconds=float(self._timeout_seconds),
                cancel_event=self.cancel_event,
                progress_callback=self._on_progress,
            )
        except Exception as exc:  # noqa: BLE001 - surface through Qt signal
            self.failed.emit(str(exc))
            return
        self.completed.emit(outcome)

    def _on_progress(self, percent: int, message: str, scanner_name: str) -> None:
        self.progress.emit(percent, message, scanner_name)

    def request_cancel(self) -> None:
        self.cancel_event.set()


class SourceAuditPage(QWidget):
    scanning_changed = Signal(bool)

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._scan_service = context.scan_service
        self._clock = context.clock
        self._worker: ScanWorker | None = None
        self._busy = False
        self._task: ScanTask | None = None
        self._path_decision = None
        self._findings: list[Finding] = []
        self._findings_by_id: dict[int, Finding] = {}
        self._scan_project_id: int | None = None
        self._scanner_infos = {
            info.name: info for info in self._scan_service.scanner_infos()
        }
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
                "源代码审计",
                "仅对当前项目登记的本地目录执行 Bandit / Semgrep 静态分析；不执行目标代码。",
                "第三阶段 · 本地只读",
            ),
            1,
        )
        self.refresh_button = button("刷新")
        self.refresh_button.clicked.connect(self.refresh_all)
        header_row.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_row)

        layout.addWidget(self._build_project_card())
        layout.addWidget(self._build_scan_card())
        layout.addLayout(self._build_findings_header())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        self.findings_table = configure_table(
            ["风险", "标题", "分类", "文件", "行号", "扫描器", "置信度"]
        )
        self.findings_table.itemSelectionChanged.connect(self._show_selected_finding)
        splitter.addWidget(self.findings_table)
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([720, 360])
        layout.addWidget(splitter, 1)

        self.empty_label = QLabel("暂无检测结果。")
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

        self.path_reason = QLabel("请选择当前项目。")
        self.path_reason.setObjectName("muted")
        self.path_reason.setWordWrap(True)
        layout.addWidget(self.path_reason)
        return card

    def _build_scan_card(self) -> QFrame:
        card = QFrame()
        card.setObjectName("card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        top = QHBoxLayout()
        top.setSpacing(16)
        scanner_title = QLabel("扫描器")
        scanner_title.setObjectName("sectionTitle")
        top.addWidget(scanner_title)
        self.scanner_checkboxes: dict[str, QCheckBox] = {}
        self.scanner_state_labels: dict[str, QLabel] = {}
        for name, info in self._scanner_infos.items():
            checkbox = QCheckBox(f"{info.display_name} {info.version}".strip())
            checkbox.setChecked(info.available)
            checkbox.setEnabled(info.available)
            if not info.available:
                checkbox.setToolTip(info.reason)
            top.addWidget(checkbox)
            state = QLabel("可用" if info.available else "不可用")
            state.setStyleSheet(
                f"color: {status_color('正常' if info.available else '拒绝')};"
            )
            if not info.available:
                state.setToolTip(info.reason)
            top.addWidget(state)
            self.scanner_checkboxes[name] = checkbox
            self.scanner_state_labels[name] = state
        top.addStretch(1)
        timeout_label = QLabel("超时")
        timeout_label.setObjectName("muted")
        top.addWidget(timeout_label)
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(30, 600)
        self.timeout_spin.setValue(180)
        self.timeout_spin.setSuffix(" 秒")
        self.timeout_spin.setFixedWidth(94)
        top.addWidget(self.timeout_spin)
        self.start_button = button("开始扫描", "primary")
        self.start_button.clicked.connect(self._start_scan)
        top.addWidget(self.start_button)
        self.cancel_button = button("取消扫描", "danger")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_scan)
        top.addWidget(self.cancel_button)
        layout.addLayout(top)

        self.scanner_notes = QLabel("")
        self.scanner_notes.setObjectName("muted")
        self.scanner_notes.setWordWrap(True)
        layout.addWidget(self.scanner_notes)

        progress_row = QHBoxLayout()
        progress_row.setSpacing(10)
        self.scan_status = QLabel("空闲")
        self.scan_status.setObjectName("pill")
        self.scan_status.setProperty("level", "muted")
        progress_row.addWidget(self.scan_status)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_row.addWidget(self.progress_bar, 1)
        self.current_scanner_label = QLabel("当前扫描器：—")
        self.current_scanner_label.setObjectName("muted")
        progress_row.addWidget(self.current_scanner_label)
        layout.addLayout(progress_row)

        self.task_summary = QLabel("尚未运行扫描任务。")
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

    def _build_findings_header(self) -> QHBoxLayout:
        row = QHBoxLayout()
        title = QLabel("检测结果")
        title.setObjectName("sectionTitle")
        row.addWidget(title)
        row.addSpacing(16)
        severity_label = QLabel("风险")
        severity_label.setObjectName("muted")
        row.addWidget(severity_label)
        self.severity_filter = QComboBox()
        self.severity_filter.addItem("全部风险", None)
        for label, value in Severity.options():
            self.severity_filter.addItem(label, value.value)
        self.severity_filter.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self.severity_filter)
        scanner_label = QLabel("扫描器")
        scanner_label.setObjectName("muted")
        row.addWidget(scanner_label)
        self.scanner_filter = QComboBox()
        self.scanner_filter.addItem("全部扫描器", None)
        for info in self._scanner_infos.values():
            self.scanner_filter.addItem(info.display_name, info.name)
        self.scanner_filter.currentIndexChanged.connect(self._apply_filters)
        row.addWidget(self.scanner_filter)
        self.filter_button = button("刷新结果", "ghost")
        self.filter_button.clicked.connect(self._refresh_findings)
        row.addWidget(self.filter_button)
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
        description_label = QLabel("说明")
        description_label.setObjectName("muted")
        layout.addWidget(description_label)
        self.detail_description = QPlainTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMinimumHeight(85)
        layout.addWidget(self.detail_description, 1)
        recommendation_label = QLabel("修复建议")
        recommendation_label.setObjectName("muted")
        layout.addWidget(recommendation_label)
        self.detail_recommendation = QPlainTextEdit()
        self.detail_recommendation.setReadOnly(True)
        self.detail_recommendation.setMinimumHeight(80)
        layout.addWidget(self.detail_recommendation, 1)
        return card

    # ------------------------------------------------------------------ refresh
    def refresh_all(self) -> None:
        self._refresh_project_info()
        self._refresh_scanner_availability()
        if not self._busy:
            self._load_latest_task()
        self._update_controls()

    def _on_project_changed(self, _project) -> None:
        if self._busy:
            return
        self.refresh_all()

    def _current_project(self):
        return self._state.current_project

    def _refresh_project_info(self) -> None:
        project = self._current_project()
        if project is None:
            self.project_name_label.setText("未选择活动项目")
            self.path_value.setText("—")
            self.path_reason.setText("请先在项目管理中设置当前项目。")
            self._set_path_pill("未选择", "muted")
            self.register_button.hide()
            self._path_decision = None
            self._update_controls()
            return
        self.project_name_label.setText(f"#{project.project_id}  {project.project_name}")
        self.path_value.setText(project.local_path or "未配置本地路径")
        if not project.local_path.strip():
            self._path_decision = None
            self.path_reason.setText("当前项目没有本地代码路径；请先在项目管理中设置。")
            self._set_path_pill("未配置路径", "warning")
            self.register_button.hide()
            self._update_controls()
            return
        try:
            decision = self._context.scope_validator.check_local_path(
                project.project_id, project.local_path, operation="source_audit"
            )
        except Exception as exc:
            self._path_decision = None
            self.path_reason.setText(f"路径校验异常：{exc}")
            self._set_path_pill("校验异常", "danger")
            self.register_button.hide()
            self._update_controls()
            return
        self._path_decision = decision
        if decision.allowed:
            self.path_reason.setText(
                f"路径校验通过，扫描范围：{decision.target}"
            )
            self._set_path_pill("已授权", "success")
            self.register_button.hide()
        else:
            self.path_reason.setText(f"路径未通过：{decision.reason}（{decision.code}）")
            self._set_path_pill("未通过", "danger")
            can_register = (
                decision.code == "local_target_not_in_scope"
                and Path(project.local_path).is_dir()
            )
            self.register_button.setVisible(can_register)
        self._update_controls()

    def _set_path_pill(self, text: str, level: str) -> None:
        self.path_pill.setText(text)
        self.path_pill.setProperty("level", level)
        self.path_pill.style().unpolish(self.path_pill)
        self.path_pill.style().polish(self.path_pill)

    def _refresh_scanner_availability(self) -> None:
        try:
            infos = {item.name: item for item in self._scan_service.scanner_infos()}
        except Exception as exc:
            self.scanner_notes.setText(f"扫描器状态检查失败：{exc}")
            return
        self._scanner_infos = infos
        reasons: list[str] = []
        for name, info in infos.items():
            checkbox = self.scanner_checkboxes.get(name)
            state = self.scanner_state_labels.get(name)
            if checkbox is None or state is None:
                continue
            checkbox.setEnabled(info.available and not self._busy)
            if not info.available:
                checkbox.setChecked(False)
                checkbox.setToolTip(info.reason)
                state.setText("不可用")
                state.setStyleSheet(f"color: {status_color('拒绝')};")
                state.setToolTip(info.reason)
                reasons.append(f"{info.display_name} 不可用：{info.reason}")
            else:
                state.setText("可用")
                state.setStyleSheet(f"color: {status_color('正常')};")
                state.setToolTip(info.command)
        self.scanner_notes.setText("  |  ".join(reasons))
        self.scanner_notes.setVisible(bool(reasons))

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
            task = self._scan_service.latest_task(project.project_id)
        except Exception as exc:
            show_error(self, exc, "读取扫描任务失败")
            return
        self._task = task
        self._current_task_id = task.task_id if task else None
        self._update_task_display()
        self._refresh_findings()

    def _update_task_display(self) -> None:
        task = self._task
        if task is None:
            self.scan_status.setText("空闲")
            self.scan_status.setProperty("level", "muted")
            self.progress_bar.setValue(0)
            self.current_scanner_label.setText("当前扫描器：—")
            self.task_summary.setText("尚未运行扫描任务。")
            self.task_meta.setText("")
            self.error_label.hide()
            self._repolish_status()
            return
        level = {
            ScanTaskStatus.PENDING: "muted",
            ScanTaskStatus.RUNNING: "info",
            ScanTaskStatus.COMPLETED: "success",
            ScanTaskStatus.FAILED: "danger",
            ScanTaskStatus.CANCELLED: "warning",
            ScanTaskStatus.BLOCKED: "warning",
        }[task.status]
        self.scan_status.setText(task.status_label)
        self.scan_status.setProperty("level", level)
        self.progress_bar.setValue(task.progress)
        self.current_scanner_label.setText(
            f"当前扫描器：{task.current_scanner or '—'}"
        )
        self.task_summary.setText(task.result_summary or "任务已创建，等待执行。")
        started = local_display(task.started_at, with_seconds=True) if task.started_at else "—"
        finished = (
            local_display(task.finished_at, with_seconds=True) if task.finished_at else "—"
        )
        self.task_meta.setText(
            f"任务 #{task.task_id} · {task.type_label} · 开始 {started} · 结束 {finished}"
        )
        if task.error_message:
            self.error_label.setText(task.error_message)
            self.error_label.show()
        else:
            self.error_label.hide()
        self._repolish_status()

    def _repolish_status(self) -> None:
        self.scan_status.style().unpolish(self.scan_status)
        self.scan_status.style().polish(self.scan_status)

    def _update_controls(self) -> None:
        project = self._current_project()
        available_selected = any(
            checkbox.isChecked()
            for name, checkbox in self.scanner_checkboxes.items()
            if self._scanner_infos.get(name) and self._scanner_infos[name].available
        )
        path_ok = bool(self._path_decision and self._path_decision.allowed)
        can_start = (
            not self._busy
            and project is not None
            and path_ok
            and available_selected
        )
        self.start_button.setEnabled(can_start)
        self.cancel_button.setEnabled(self._busy)
        self.timeout_spin.setEnabled(not self._busy)
        self.refresh_button.setEnabled(not self._busy)
        self.validate_button.setEnabled(not self._busy and project is not None)
        for name, checkbox in self.scanner_checkboxes.items():
            info = self._scanner_infos.get(name)
            checkbox.setEnabled(bool(info and info.available) and not self._busy)

    # ------------------------------------------------------------------ scan
    def _start_scan(self) -> None:
        if self._busy:
            return
        project = self._current_project()
        if project is None:
            self.error_label.setText("请先选择当前项目。")
            self.error_label.show()
            return
        self.refresh_all()
        if not self._path_decision or not self._path_decision.allowed:
            self.error_label.setText("本地路径尚未通过校验，不能启动扫描。")
            self.error_label.show()
            return
        names = [
            name
            for name, checkbox in self.scanner_checkboxes.items()
            if checkbox.isChecked()
            and name in self._scanner_infos
            and self._scanner_infos[name].available
        ]
        if not names:
            self.error_label.setText("没有可用的扫描器被选中。")
            self.error_label.show()
            return
        self._scan_project_id = project.project_id
        self._set_busy(True)
        self.error_label.hide()
        self.task_summary.setText("扫描任务启动中…")
        self.progress_bar.setValue(0)
        self.scan_status.setText("等待中")
        self.scan_status.setProperty("level", "info")
        self._repolish_status()
        self.current_scanner_label.setText("当前扫描器：准备中")
        worker = ScanWorker(
            self._scan_service,
            project.project_id,
            names,
            self.timeout_spin.value(),
            self,
        )
        worker.progress.connect(self._on_scan_progress)
        worker.completed.connect(self._on_scan_completed)
        worker.failed.connect(self._on_scan_failed)
        worker.finished.connect(self._on_worker_finished)
        self._worker = worker
        worker.start()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.scanning_changed.emit(busy)
        self._update_controls()

    def _cancel_scan(self) -> None:
        if self._worker is None or not self._busy:
            return
        self._worker.request_cancel()
        self.cancel_button.setEnabled(False)
        self.scan_status.setText("取消中…")
        self.scan_status.setProperty("level", "warning")
        self._repolish_status()
        self.task_summary.setText("正在请求取消当前扫描任务…")

    def _on_scan_progress(self, percent: int, message: str, scanner_name: str) -> None:
        self.progress_bar.setValue(percent)
        self.task_summary.setText(message)
        display = self._scanner_infos.get(scanner_name)
        self.current_scanner_label.setText(
            f"当前扫描器：{display.display_name if display else (scanner_name or '—')}"
        )
        if not (self._worker is not None and self._worker.cancel_event.is_set()):
            self.scan_status.setText("扫描中")
            self.scan_status.setProperty("level", "info")
            self._repolish_status()

    def _on_scan_completed(self, outcome: ScanOutcome) -> None:
        self._task = outcome.task
        self._current_task_id = outcome.task.task_id
        self._update_task_display()
        self._refresh_findings()
        notices = list(outcome.warnings) + list(outcome.errors)
        if notices:
            self.error_label.setText("\n".join(notices[:10]))
            self.error_label.show()
        elif outcome.success and not outcome.findings:
            self.task_summary.setText(outcome.task.result_summary or "扫描完成，未发现问题。")

    def _on_scan_failed(self, message: str) -> None:
        self._load_latest_task()
        self.error_label.setText(message)
        self.error_label.show()
        self.scan_status.setText("失败")
        self.scan_status.setProperty("level", "danger")
        self._repolish_status()
        self.task_summary.setText("扫描任务异常终止。")

    def _on_worker_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._set_busy(False)
        self._refresh_scanner_availability()
        self._update_controls()
        if (
            self._scan_project_id is not None
            and self._current_project() is not None
            and self._current_project().project_id != self._scan_project_id
        ):
            self.refresh_all()
        self._scan_project_id = None

    # ------------------------------------------------------------------ findings
    def _apply_filters(self) -> None:
        self._refresh_findings()

    def _refresh_findings(self) -> None:
        project = self._current_project()
        if project is None or self._current_task_id is None:
            self._findings = []
            self._findings_by_id = {}
            self.findings_table.setRowCount(0)
            self.count_label.setText("0 个结果")
            self.empty_label.setText("暂无检测结果。")
            self._clear_detail()
            return
        try:
            findings = self._scan_service.list_findings(
                project.project_id,
                task_id=self._current_task_id,
                severity=self.severity_filter.currentData(),
                scanner_name=self.scanner_filter.currentData(),
                limit=2000,
            )
        except Exception as exc:
            show_error(self, exc, "读取检测结果失败")
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
            values = [
                table_item(finding.severity_label, color=status_color(finding.severity_label)),
                table_item(finding.title),
                table_item(finding.category or "—"),
                table_item(finding.file_path or "—"),
                table_item(finding.line_display),
                table_item(finding.scanner_label),
                table_item(finding.confidence_label),
            ]
            if finding.finding_id is not None:
                values[0].setData(Qt.ItemDataRole.UserRole, finding.finding_id)
            for column, item in enumerate(values):
                self.findings_table.setItem(row_index, column, item)
        header = self.findings_table.horizontalHeader()
        header.setStretchLastSection(False)
        for column, width in enumerate([56, 150, 98, 165, 44, 70, 64]):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.findings_table.setColumnWidth(column, width)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.count_label.setText(f"{len(findings)} 个结果")
        if findings:
            empty_text = ""
        elif self._task is not None and self._task.status is ScanTaskStatus.COMPLETED:
            empty_text = "扫描完成，未发现匹配的安全问题。"
        elif self._task is not None and self._task.status is ScanTaskStatus.FAILED:
            empty_text = "任务失败，未产生检测结果。"
        elif self._task is not None and self._task.status is ScanTaskStatus.CANCELLED:
            empty_text = "任务已取消，未产生检测结果。"
        else:
            empty_text = "当前筛选条件下没有检测结果。"
        self.empty_label.setText(empty_text)
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
        self.detail_title.setText(finding.title)
        self.detail_meta.setText(
            f"{finding.file_path}:{finding.line_number}  ·  "
            f"{finding.scanner_label} {finding.scanner_version}  ·  "
            f"规则 {finding.rule_id or '—'}  ·  置信度 {finding.confidence_label}"
        )
        self.detail_description.setPlainText(finding.description or "—")
        self.detail_recommendation.setPlainText(finding.recommendation or "—")

    def _clear_detail(self) -> None:
        self.detail_title.setText("暂无结果")
        self.detail_meta.setText("尚未选择检测结果。")
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
                notes="源代码审计页面登记",
            )
        except ConflictError:
            pass
        except AppError as exc:
            show_error(self, exc, "登记本地资产失败")
            return
        except Exception as exc:
            show_error(self, exc, "登记本地资产失败")
            return
        self.refresh_all()

    def shutdown(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.request_cancel()
            if not self._worker.wait(15000):
                self._worker.wait(5000)
