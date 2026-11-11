"""Evidence center page with project-scoped files and text evidence."""

from __future__ import annotations

from PySide6.QtCore import QThread, QTimer, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.models import Evidence, EvidenceType
from core.timeutil import local_display
from services.evidence_service import SENSITIVE_WARNING
from ui.app_state import AppState
from ui.evidence_dialog import EvidenceDialog
from ui.widgets import (
    button,
    configure_table,
    confirm,
    notice_frame,
    page_header,
    selected_id,
    show_error,
    table_item,
)


class EvidenceListWorker(QThread):
    loaded = Signal(int, object)
    failed = Signal(int, str)

    def __init__(self, service, generation: int, filters: dict, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._generation = generation
        self._filters = filters

    def run(self) -> None:
        try:
            evidence = self._service.list_evidence(**self._filters)
        except Exception as exc:  # noqa: BLE001 - delivered through Qt
            self.failed.emit(self._generation, str(exc))
            return
        self.loaded.emit(self._generation, evidence)


class EvidencePage(QWidget):
    data_loaded = Signal(int)
    open_vulnerability_requested = Signal(int, int)

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._service = context.evidence_service
        self._worker: EvidenceListWorker | None = None
        self._generation = 0
        self._pending_refresh = False
        self._shutting_down = False
        self._evidence: list[Evidence] = []
        self._evidence_by_id: dict[int, Evidence] = {}
        self._pending_select: int | None = None
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self.refresh)
        self._build_ui()
        self._populate_projects()
        self._state.project_changed.connect(self._on_project_changed)
        self.refresh()

    # ------------------------------------------------------------------ build
    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 22, 28, 22)
        layout.setSpacing(11)
        header = QHBoxLayout()
        header.addWidget(
            page_header(
                "证据中心",
                "保存与漏洞关联的代码片段、扫描摘要、依赖信息、截图和人工备注；所有文件均受项目路径校验。",
                "第五阶段 · 项目证据",
            ),
            1,
        )
        self.refresh_button = button("刷新")
        self.refresh_button.clicked.connect(self.refresh)
        header.addWidget(self.refresh_button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header)
        layout.addWidget(notice_frame(SENSITIVE_WARNING, "warning"))

        filters = QFrame()
        filters.setObjectName("card")
        filter_layout = QHBoxLayout(filters)
        filter_layout.setContentsMargins(14, 10, 14, 10)
        filter_layout.setSpacing(8)
        self.project_filter = QComboBox()
        self.project_filter.setMinimumWidth(190)
        self.project_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.project_filter)
        self.type_filter = QComboBox()
        self.type_filter.addItem("全部类型", None)
        for label, value in EvidenceType.options():
            self.type_filter.addItem(label, value.value)
        self.type_filter.currentIndexChanged.connect(self.refresh)
        filter_layout.addWidget(self.type_filter)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索证据标题、内容、文件名或漏洞")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(lambda: self._timer.start())
        filter_layout.addWidget(self.search_edit, 1)
        self.add_button = button("添加证据", "primary")
        self.add_button.clicked.connect(self._add_evidence)
        filter_layout.addWidget(self.add_button)
        layout.addWidget(filters)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)
        self.table = configure_table(
            ["标题", "类型", "项目", "关联漏洞", "文件 / 来源", "哈希", "创建时间"]
        )
        self.table.itemSelectionChanged.connect(self._selection_changed)
        left_layout.addWidget(self.table, 1)
        self.count_label = QLabel("0 份证据")
        self.count_label.setObjectName("muted")
        left_layout.addWidget(self.count_label)
        splitter.addWidget(left)
        splitter.addWidget(self._build_detail())
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([800, 450])
        layout.addWidget(splitter, 1)
        self.empty_label = QLabel("暂无证据记录。")
        self.empty_label.setObjectName("muted")
        layout.addWidget(self.empty_label)

    def _build_detail(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(14, 10, 10, 10)
        layout.setSpacing(8)
        title = QLabel("证据详情")
        title.setObjectName("sectionTitle")
        layout.addWidget(title)
        self.detail_title = QLabel("选择一份证据查看详情")
        self.detail_title.setWordWrap(True)
        self.detail_title.setStyleSheet("font-weight: 600; color: #e7eef9;")
        layout.addWidget(self.detail_title)
        self.detail_meta = QLabel("")
        self.detail_meta.setWordWrap(True)
        self.detail_meta.setObjectName("muted")
        self.detail_meta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.detail_meta)
        layout.addWidget(self._section("证据内容"))
        self.detail_description = QPlainTextEdit()
        self.detail_description.setReadOnly(True)
        self.detail_description.setMinimumHeight(170)
        layout.addWidget(self.detail_description)
        layout.addWidget(self._section("文件与完整性"))
        self.detail_file = QPlainTextEdit()
        self.detail_file.setReadOnly(True)
        self.detail_file.setMinimumHeight(110)
        layout.addWidget(self.detail_file)
        layout.addWidget(self._section("项目与漏洞关联"))
        self.detail_relation = QLabel("")
        self.detail_relation.setWordWrap(True)
        self.detail_relation.setObjectName("muted")
        self.detail_relation.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.detail_relation)

        buttons = QHBoxLayout()
        self.open_finding_button = button("查看关联漏洞", "primary")
        self.open_finding_button.clicked.connect(self._open_finding)
        buttons.addWidget(self.open_finding_button)
        buttons.addStretch(1)
        self.delete_button = button("删除证据", "danger")
        self.delete_button.clicked.connect(self._delete_evidence)
        buttons.addWidget(self.delete_button)
        layout.addLayout(buttons)
        layout.addStretch(1)
        scroll.setWidget(inner)
        return scroll

    @staticmethod
    def _section(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _populate_projects(self) -> None:
        active = self._state.current_project_id
        self.project_filter.blockSignals(True)
        self.project_filter.clear()
        self.project_filter.addItem("全部项目", None)
        try:
            projects = self._context.project_service.list_projects()
        except Exception:
            projects = []
        for project in projects:
            self.project_filter.addItem(
                f"#{project.project_id}  {project.project_name}", project.project_id
            )
        index = self.project_filter.findData(active) if active is not None else 0
        self.project_filter.setCurrentIndex(max(0, index))
        self.project_filter.blockSignals(False)

    # ------------------------------------------------------------------ loading
    def refresh(self) -> None:
        if self._shutting_down:
            return
        self._generation += 1
        generation = self._generation
        if self._worker is not None and self._worker.isRunning():
            self._pending_refresh = True
            return
        filters = {
            "project_id": self.project_filter.currentData(),
            "evidence_type": self.type_filter.currentData(),
            "keyword": self.search_edit.text().strip(),
            "limit": 1000,
        }
        worker = EvidenceListWorker(self._service, generation, filters, self)
        worker.setObjectName(f"EvidenceListWorker-{generation}")
        worker.loaded.connect(self._on_loaded)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(
            lambda completed_worker=worker: self._on_worker_finished(completed_worker)
        )
        self._worker = worker
        self.refresh_button.setEnabled(False)
        worker.start()

    def _on_loaded(self, generation: int, evidence: list[Evidence]) -> None:
        if generation != self._generation:
            return
        selected = self._pending_select or selected_id(self.table)
        self._evidence = evidence
        self._evidence_by_id = {
            item.evidence_id: item for item in evidence
        }
        self.table.setRowCount(0)
        for row_index, item in enumerate(evidence):
            self.table.insertRow(row_index)
            file_or_source = item.file_name or item.source or "—"
            values = [
                table_item(item.display_title),
                table_item(item.type_label),
                table_item(item.project_name or "—"),
                table_item(item.finding_title or "—"),
                table_item(file_or_source),
                table_item(item.short_hash),
                table_item(item.created_at.strftime("%Y-%m-%d")),
            ]
            if item.evidence_id is not None:
                values[0].setData(Qt.ItemDataRole.UserRole, item.evidence_id)
            for column, cell in enumerate(values):
                self.table.setItem(row_index, column, cell)
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        for column, width in enumerate([170, 90, 88, 105, 95, 80, 100]):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.count_label.setText(f"{len(evidence)} 份证据")
        self.empty_label.setVisible(not evidence)
        target_row = -1
        for row_index, item in enumerate(evidence):
            if item.evidence_id == selected:
                target_row = row_index
                break
        if target_row >= 0:
            self.table.selectRow(target_row)
        elif evidence:
            self.table.selectRow(0)
        else:
            self._clear_detail()
        self._pending_select = None
        self.data_loaded.emit(len(evidence))

    def _on_failed(self, generation: int, message: str) -> None:
        if generation == self._generation:
            show_error(self, Exception(message), "读取证据列表失败")
            self.count_label.setText("读取失败")

    def _on_worker_finished(self, worker) -> None:
        if self._worker is worker:
            self._worker = None
            self.refresh_button.setEnabled(True)
            if self._pending_refresh and not self._shutting_down:
                self._pending_refresh = False
                QTimer.singleShot(0, self.refresh)
        if worker is not None:
            worker.deleteLater()

    def _selection_changed(self) -> None:
        evidence_id = selected_id(self.table)
        if evidence_id is None:
            self._clear_detail()
            return
        item = self._evidence_by_id.get(evidence_id)
        if item is None:
            return
        try:
            self._render_detail(self._service.get_evidence(item.project_id, evidence_id))
        except Exception as exc:
            show_error(self, exc, "读取证据详情失败")

    def _render_detail(self, evidence: Evidence) -> None:
        self.detail_title.setText(evidence.display_title)
        self.detail_meta.setText(
            f"类型：{evidence.type_label}  ·  证据 ID：#{evidence.evidence_id}  ·  "
            f"项目：{evidence.project_name}  ·  "
            f"创建时间：{local_display(evidence.created_at, with_seconds=True)}"
        )
        self.detail_description.setPlainText(evidence.description or "—")
        path = evidence.file_path or "—"
        self.detail_file.setPlainText(
            f"文件路径：{path}\n"
            f"原始文件名：{evidence.file_name or '—'}\n"
            f"来源：{evidence.source or '—'}\n"
            f"SHA-256：{evidence.file_hash or '—'}"
        )
        self.detail_relation.setText(
            f"关联漏洞：{evidence.finding_title or '—'}\n"
            f"漏洞 ID：#{evidence.finding_id}"
        )
        self.open_finding_button.setEnabled(evidence.finding_id > 0)
        self.delete_button.setEnabled(True)

    def _clear_detail(self) -> None:
        self.detail_title.setText("选择一份证据查看详情")
        self.detail_meta.setText("")
        self.detail_description.clear()
        self.detail_file.clear()
        self.detail_relation.clear()
        self.open_finding_button.setEnabled(False)
        self.delete_button.setEnabled(False)

    # ------------------------------------------------------------------ actions
    def _add_evidence(self) -> None:
        dialog = EvidenceDialog(
            self._context,
            initial_project_id=self.project_filter.currentData(),
            parent=self,
        )
        if dialog.exec() == EvidenceDialog.DialogCode.Accepted:
            if dialog.created_evidence is not None:
                self._pending_select = dialog.created_evidence.evidence_id
            self.refresh()

    def _delete_evidence(self) -> None:
        evidence_id = selected_id(self.table)
        if evidence_id is None:
            return
        evidence = self._evidence_by_id.get(evidence_id)
        if evidence is None:
            return
        if not confirm(
            self,
            "删除证据",
            f"确定删除证据“{evidence.display_title}”吗？\n\n"
            "只删除证据记录和受管副本，不会删除原始文件，也不会删除关联漏洞。",
            dangerous=True,
        ):
            return
        try:
            self._service.delete_evidence(evidence.project_id, evidence_id)
        except Exception as exc:
            show_error(self, exc, "删除证据失败")
            return
        self.refresh()

    def _open_finding(self) -> None:
        evidence_id = selected_id(self.table)
        if evidence_id is None:
            return
        evidence = self._evidence_by_id.get(evidence_id)
        if evidence is None or evidence.finding_id <= 0:
            return
        self.open_vulnerability_requested.emit(
            evidence.project_id, evidence.finding_id
        )

    # ------------------------------------------------------------------ external
    def select_evidence(
        self, project_id: int, finding_id: int, evidence_id: int | None = None
    ) -> None:
        index = self.project_filter.findData(project_id)
        if index >= 0:
            self.project_filter.blockSignals(True)
            self.project_filter.setCurrentIndex(index)
            self.project_filter.blockSignals(False)
        self._pending_select = evidence_id
        self.refresh()

    def _on_project_changed(self, _project) -> None:
        active = self._state.current_project_id
        index = self.project_filter.findData(active) if active is not None else 0
        self.project_filter.blockSignals(True)
        self.project_filter.setCurrentIndex(max(0, index))
        self.project_filter.blockSignals(False)
        self.refresh()

    def shutdown(self) -> None:
        self._shutting_down = True
        self._pending_refresh = False
        self._timer.stop()
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(15000)
