"""Report center: safe HTML preview and export for one active project."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.errors import ValidationError
from core.models.report import (
    ReportArtifact,
    ReportFormat,
    ReportRequest,
    ReportSnapshot,
    ReportType,
)
from reports.html_exporter import render_html, write_html_report
from ui.app_state import AppState
from ui.widgets import (
    button,
    confirm,
    notice_frame,
    page_header,
    show_error,
)


class ReportPage(QWidget):
    """Minimal report center backed by the read-only ReportService.

    The page never constructs a repository/database and never writes a file
    directly.  ``render_html()`` is used only for the in-memory preview;
    ``write_html_report()`` is the sole publication path.
    """

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._service = context.report_service
        self._reports_dir = context.config.reports_dir
        self._snapshot: ReportSnapshot | None = None
        self._snapshot_project_id: int | None = None
        self._snapshot_type: ReportType | None = None
        self._exporting = False
        self._build_ui()
        self._state.project_changed.connect(self._on_project_changed)
        self.refresh()

    # ------------------------------------------------------------------ UI
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(11)

        header = QHBoxLayout()
        header.addWidget(
            page_header(
                "报告中心",
                "从当前项目的只读快照生成安全 HTML 报告；不访问远程目标，不自动上传。",
                "第六阶段 · HTML 报告",
            ),
            1,
        )
        self.refresh_button = button("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)

        layout.addWidget(
            notice_frame(
                "报告只覆盖当前活动项目；正式文件固定写入应用报告目录。"
                "预览是安全文本预览，不保证与浏览器排版一致。",
                "warning",
            )
        )

        project_card = QFrame()
        project_card.setObjectName("card")
        project_layout = QVBoxLayout(project_card)
        project_layout.setContentsMargins(16, 12, 16, 12)
        project_layout.setSpacing(5)
        project_row = QHBoxLayout()
        project_row.setSpacing(10)
        project_title = QLabel("当前项目")
        project_title.setObjectName("sectionTitle")
        project_row.addWidget(project_title)
        self.project_label = QLabel("未选择活动项目")
        self.project_label.setWordWrap(True)
        self.project_label.setStyleSheet("font-weight: 600; color: #e7eef9;")
        project_row.addWidget(self.project_label, 1)
        project_layout.addLayout(project_row)
        self.project_meta = QLabel("")
        self.project_meta.setObjectName("muted")
        self.project_meta.setWordWrap(True)
        project_layout.addWidget(self.project_meta)
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)
        dir_caption = QLabel("输出目录")
        dir_caption.setObjectName("muted")
        dir_row.addWidget(dir_caption)
        self.reports_dir_label = QLabel(str(self._reports_dir))
        self.reports_dir_label.setObjectName("formHint")
        self.reports_dir_label.setWordWrap(True)
        self.reports_dir_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        dir_row.addWidget(self.reports_dir_label, 1)
        project_layout.addLayout(dir_row)
        layout.addWidget(project_card)

        options_card = QFrame()
        options_card.setObjectName("card")
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(16, 12, 16, 12)
        options_layout.setSpacing(8)

        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_caption = QLabel("报告类型")
        type_caption.setObjectName("muted")
        type_row.addWidget(type_caption)
        self.report_type_combo = QComboBox()
        self.report_type_combo.setMinimumWidth(220)
        for label, report_type in ReportType.options():
            self.report_type_combo.addItem(label, report_type)
        type_row.addWidget(self.report_type_combo)
        type_row.addStretch(1)
        options_layout.addLayout(type_row)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        title_caption = QLabel("报告标题")
        title_caption.setObjectName("muted")
        title_row.addWidget(title_caption)
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(200)
        self.title_edit.setPlaceholderText("留空则使用默认标题（最多 200 字符）")
        self.title_edit.setClearButtonEnabled(True)
        title_row.addWidget(self.title_edit, 1)
        options_layout.addLayout(title_row)

        option_row = QHBoxLayout()
        option_row.setSpacing(12)
        self.include_notes_check = QCheckBox("包含人工处理备注")
        self.include_notes_check.setChecked(True)
        self.include_notes_check.setToolTip(
            "关闭后，报告不展示 Finding 的人工备注；不会修改数据库。"
        )
        option_row.addWidget(self.include_notes_check)
        self.filename_label = QLabel("文件名：由安全导出器自动生成")
        self.filename_label.setObjectName("formHint")
        option_row.addWidget(self.filename_label)
        option_row.addStretch(1)
        options_layout.addLayout(option_row)
        layout.addWidget(options_card)

        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        self.status_label = QLabel("请先生成预览。")
        self.status_label.setObjectName("muted")
        self.status_label.setWordWrap(True)
        action_row.addWidget(self.status_label, 1)
        self.preview_button = button("生成预览")
        self.preview_button.clicked.connect(self.generate_preview)
        action_row.addWidget(self.preview_button)
        self.export_button = button("导出 HTML", "primary")
        self.export_button.clicked.connect(self.export)
        action_row.addWidget(self.export_button)
        layout.addLayout(action_row)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_layout = QVBoxLayout(summary_card)
        summary_layout.setContentsMargins(16, 14, 16, 14)
        summary_layout.setSpacing(8)
        summary_title = QLabel("报告摘要")
        summary_title.setObjectName("sectionTitle")
        summary_layout.addWidget(summary_title)
        self.summary_label = QLabel("选择项目并生成预览后显示快照摘要。")
        self.summary_label.setObjectName("muted")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        summary_layout.addWidget(self.summary_label)
        summary_layout.addStretch(1)
        self.output_label = QLabel("")
        self.output_label.setObjectName("formHint")
        self.output_label.setWordWrap(True)
        self.output_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        summary_layout.addWidget(self.output_label)
        splitter.addWidget(summary_card)

        preview_card = QFrame()
        preview_card.setObjectName("card")
        preview_layout = QVBoxLayout(preview_card)
        preview_layout.setContentsMargins(14, 12, 14, 12)
        preview_layout.setSpacing(6)
        preview_heading = QLabel("HTML 预览")
        preview_heading.setObjectName("sectionTitle")
        preview_layout.addWidget(preview_heading)
        preview_hint = QLabel("安全文本预览（非浏览器排版）")
        preview_hint.setObjectName("formHint")
        preview_layout.addWidget(preview_hint)
        self.preview = QTextBrowser()
        self.preview.setObjectName("reportPreview")
        self.preview.setOpenExternalLinks(False)
        self.preview.setOpenLinks(False)
        self.preview.setStyleSheet(
            "QTextBrowser#reportPreview { background: #0b1422; "
            "border: 1px solid #203048; border-radius: 8px; padding: 8px; }"
        )
        self.preview.setPlainText("请先生成预览。")
        preview_layout.addWidget(self.preview, 1)
        splitter.addWidget(preview_card)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 920])
        layout.addWidget(splitter, 1)

        self.report_type_combo.currentIndexChanged.connect(
            self._on_report_type_changed
        )
        self.title_edit.textChanged.connect(self._on_request_changed)
        self.include_notes_check.toggled.connect(self._on_request_changed)
        self._update_controls()

    # ------------------------------------------------------------------ state
    def refresh(self) -> None:
        project = self._state.current_project
        if project is None:
            self.project_label.setText("未选择活动项目")
            self.project_meta.setText("请先在顶部选择当前项目，再生成报告。")
            self._invalidate_snapshot(clear_preview=True)
            self._set_status("未选择活动项目。")
        else:
            self.project_label.setText(
                f"#{project.project_id}  {project.project_name}"
            )
            self.project_meta.setText(
                f"类型：{project.type_label}  ·  状态：{project.status_label}"
            )
            # A manual refresh is also a request for fresh page state.  Never
            # keep an old preview visible next to an explicitly refreshed page.
            self._invalidate_snapshot(clear_preview=True)
            self._set_status("请先生成预览，确认内容后再导出。")
        self._update_controls()

    def _on_project_changed(self, _project) -> None:  # type: ignore[no-untyped-def]
        self.refresh()

    def _on_report_type_changed(self, _index: int) -> None:
        self._invalidate_snapshot(clear_preview=True)
        if self._state.current_project is not None:
            self._set_status("报告类型已切换，请重新生成预览。")
        self._update_controls()

    def _on_request_changed(self, *_args) -> None:  # type: ignore[no-untyped-def]
        if self._snapshot is not None:
            self._set_status("标题或备注选项已变化；导出将使用当前参数。")
        self._update_controls()

    def _selected_type(self) -> ReportType:
        value = self.report_type_combo.currentData()
        if isinstance(value, ReportType):
            return value
        try:
            return ReportType(str(value))
        except ValueError as exc:
            raise ValidationError("报告类型无效") from exc

    # ------------------------------------------------------------------ snapshot
    def _ensure_snapshot(self, *, force: bool = False) -> ReportSnapshot:
        project_id = self._state.current_project_id
        if project_id is None:
            raise ValidationError("请先在顶部选择当前项目")
        selected_type = self._selected_type()
        if (
            not force
            and self._snapshot is not None
            and self._snapshot_project_id == project_id
            and self._snapshot_type is selected_type
        ):
            return self._snapshot
        snapshot = self._service.get_snapshot(project_id, selected_type)
        self._snapshot = snapshot
        self._snapshot_project_id = project_id
        self._snapshot_type = selected_type
        self._render_summary(snapshot)
        return snapshot

    def _invalidate_snapshot(self, *, clear_preview: bool) -> None:
        self._snapshot = None
        self._snapshot_project_id = None
        self._snapshot_type = None
        self.summary_label.setText("选择项目并生成预览后显示快照摘要。")
        self.output_label.clear()
        if clear_preview:
            self.preview.setPlainText("请先生成预览。")

    def _request_for(self, snapshot: ReportSnapshot) -> ReportRequest:
        return ReportRequest(
            project_id=snapshot.project_id,
            report_type=snapshot.report_type,
            report_format=ReportFormat.HTML,
            title=self.title_edit.text().strip(),
            include_evidence_images=False,
            include_notes=self.include_notes_check.isChecked(),
            requested_at=self._context.clock(),
        )

    # ------------------------------------------------------------------ actions
    def generate_preview(self) -> None:
        if self._exporting:
            return
        try:
            snapshot = self._ensure_snapshot(force=True)
            request = self._request_for(snapshot)
            html = render_html(snapshot, request)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            show_error(self, exc, "生成报告预览失败")
            self._set_status("预览失败；未写入任何文件。")
            return
        self.preview.setHtml(html)
        self._set_status("预览已生成，尚未写入文件。")
        self.output_label.clear()

    def export(self) -> None:
        if self._exporting:
            return
        if self._state.current_project_id is None:
            self._set_status("未选择活动项目，不能导出。")
            self._update_controls()
            return
        self._exporting = True
        self._set_busy_controls(True)
        self._set_status("正在导出 HTML 报告...")
        self.output_label.clear()
        try:
            snapshot = self._ensure_snapshot(force=True)
            request = self._request_for(snapshot)
            try:
                artifact = self._write(snapshot, request, overwrite=False)
            except FileExistsError:
                if not confirm(
                    self,
                    "覆盖报告",
                    "目标目录中已存在同名报告文件。是否覆盖？\n覆盖会替换旧文件。",
                    dangerous=True,
                ):
                    self._set_status("已取消：未覆盖现有报告。")
                    return
                artifact = self._write(snapshot, request, overwrite=True)
            self._show_artifact(artifact)
        except Exception as exc:  # noqa: BLE001 - shown to the user
            show_error(self, exc, "导出报告失败")
            self._set_status("导出失败；未显示成功结果。")
            self.output_label.clear()
        finally:
            self._exporting = False
            self._set_busy_controls(False)

    def _write(
        self,
        snapshot: ReportSnapshot,
        request: ReportRequest,
        *,
        overwrite: bool,
    ) -> ReportArtifact:
        return write_html_report(
            snapshot,
            request,
            self._reports_dir,
            overwrite=overwrite,
            filename=None,
        )

    def _show_artifact(self, artifact: ReportArtifact) -> None:
        self.output_label.setText(
            f"输出：{artifact.path}\nSHA-256：{artifact.sha256}"
        )
        self._set_status("导出成功，已生成 HTML 报告。")

    # ------------------------------------------------------------------ helpers
    def _set_status(self, text: str) -> None:
        self.status_label.setText(text)

    def _set_busy_controls(self, busy: bool) -> None:
        for control in (
            self.refresh_button,
            self.preview_button,
            self.export_button,
            self.report_type_combo,
            self.title_edit,
            self.include_notes_check,
        ):
            control.setEnabled(not busy)
        if not busy:
            self._update_controls()

    def _update_controls(self) -> None:
        has_project = self._state.current_project_id is not None
        self.preview_button.setEnabled(has_project and not self._exporting)
        self.export_button.setEnabled(has_project and not self._exporting)
        self.refresh_button.setEnabled(not self._exporting)
        self.report_type_combo.setEnabled(not self._exporting)
        self.title_edit.setEnabled(not self._exporting)
        self.include_notes_check.setEnabled(not self._exporting)

    def _render_summary(self, snapshot: ReportSnapshot) -> None:
        stats = snapshot.stats
        if stats is None:
            self.summary_label.setText("快照没有统计数据。")
            return
        authorization = snapshot.authorization
        lines = [
            f"报告类型：{snapshot.report_type.label}",
            f"项目：#{snapshot.project.project_id}  {snapshot.project.project_name}",
            f"生成时间：{snapshot.generated_at.astimezone().strftime('%Y-%m-%d %H:%M:%S')}",
            f"快照：{snapshot.snapshot_id[:12]}…",
            f"任务：{stats.task_count}  ·  Finding：{stats.finding_count}  ·  "
            f"Evidence：{stats.evidence_count}",
            f"授权：有效 {authorization.effective_count} / 总计 "
            f"{authorization.total_count}  ·  "
            f"高风险 Finding：{stats.severity_counts.get('high', 0)}",
            f"警告：{len(snapshot.warnings)} 条"
        ]
        self.summary_label.setText("\n".join(lines))
