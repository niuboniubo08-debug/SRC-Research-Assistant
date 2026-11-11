"""Project, authorization and scope-asset management page."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QDateTime, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.errors import AppError, ConflictError, NotFoundError
from core.models import (
    AssetStatus,
    AssetType,
    AuthStatus,
    Authorization,
    Project,
    ProjectStatus,
    ProjectType,
    RemoteOperation,
    ScopeAsset,
)
from core.timeutil import local_display
from services.authorization_service import AuthorizationService
from services.scope_asset_service import ScopeAssetService
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


def _qdatetime(value: datetime) -> QDateTime:
    return QDateTime.fromMSecsSinceEpoch(int(value.timestamp() * 1000))


def _read_qdatetime(edit) -> datetime:
    value = edit.dateTime().toPython()
    if value.tzinfo is None:
        value = value.astimezone()
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _inline_error(parent: QDialog) -> QLabel:
    label = QLabel("")
    label.setObjectName("errorLabel")
    label.setWordWrap(True)
    label.hide()
    return label


class ProjectDialog(QDialog):
    def __init__(self, service, project: Project | None = None, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._project = project
        self.saved_project: Project | None = None
        self.setWindowTitle("编辑项目" if project else "新建项目")
        self.setModal(True)
        self.setMinimumWidth(540)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel("编辑项目" if project else "新建安全研究项目")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        hint = QLabel("项目名称不代表授权。远程检测还需要单独、有效且已确认的授权记录。")
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.name_edit = QLineEdit(project.project_name if project else "")
        self.name_edit.setPlaceholderText("例如：客户 A 授权代码审计")
        self.name_edit.setMaxLength(120)
        form.addRow("项目名称 *", self.name_edit)

        self.type_combo = QComboBox()
        for label, value in ProjectType.options():
            self.type_combo.addItem(label, value.value)
        if project:
            self.type_combo.setCurrentIndex(self.type_combo.findData(project.project_type.value))
        form.addRow("项目类型 *", self.type_combo)

        self.status_combo = QComboBox()
        for label, value in ProjectStatus.options():
            self.status_combo.addItem(label, value.value)
        if project:
            self.status_combo.setCurrentIndex(self.status_combo.findData(project.status.value))
        form.addRow("项目状态 *", self.status_combo)

        path_row = QWidget()
        path_layout = QHBoxLayout(path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(7)
        self.path_edit = QLineEdit(project.local_path if project else "")
        self.path_edit.setPlaceholderText("可选：本地源代码绝对路径")
        path_layout.addWidget(self.path_edit, 1)
        browse = button("浏览…", "ghost")
        browse.clicked.connect(self._browse_path)
        path_layout.addWidget(browse)
        form.addRow("本地路径", path_row)

        self.description_edit = QPlainTextEdit(project.description if project else "")
        self.description_edit.setPlaceholderText("项目目标、授权背景或备注；不要粘贴与项目无关的敏感数据。")
        self.description_edit.setFixedHeight(92)
        form.addRow("项目说明", self.description_edit)
        layout.addLayout(form)

        self.error_label = _inline_error(self)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_path(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择本地项目目录", self.path_edit.text())
        if selected:
            self.path_edit.setText(selected)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _save(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            self._show_error("项目名称不能为空。")
            self.name_edit.setFocus()
            return
        path = self.path_edit.text().strip()
        if path and not Path(path).is_absolute():
            self._show_error("本地路径必须是绝对路径。")
            return
        if path and not Path(path).is_dir():
            self._show_error("本地路径不存在或不是文件夹。")
            return
        try:
            if self._project is None:
                project = self._service.create_project(
                    name,
                    self.type_combo.currentData(),
                    self.description_edit.toPlainText(),
                    path,
                    self.status_combo.currentData(),
                )
            else:
                project = self._service.update_project(
                    self._project.project_id,
                    project_name=name,
                    project_type=self.type_combo.currentData(),
                    description=self.description_edit.toPlainText(),
                    local_path=path,
                    status=self.status_combo.currentData(),
                )
        except (AppError, OSError) as exc:
            self._show_error(str(exc))
            return
        self.saved_project = project
        self.accept()


class AuthorizationDialog(QDialog):
    def __init__(
        self,
        service: AuthorizationService,
        project_id: int,
        authorization: Authorization | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._project_id = project_id
        self._authorization = authorization
        self.saved_authorization: Authorization | None = None
        self.setWindowTitle("编辑授权" if authorization else "新增授权")
        self.setModal(True)
        self.setMinimumWidth(590)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel("编辑授权记录" if authorization else "新增授权记录")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        hint = QLabel(
            "授权是否有效由后端按状态、起止时间、项目归属和资产范围共同判断。"
            "仅填写项目名称不会产生授权。"
        )
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.source_edit = QLineEdit(
            authorization.authorization_source if authorization else ""
        )
        self.source_edit.setPlaceholderText("例如：客户盖章授权书 / 合同编号")
        self.source_edit.setMaxLength(500)
        form.addRow("授权来源 *", self.source_edit)

        document_row = QWidget()
        document_layout = QHBoxLayout(document_row)
        document_layout.setContentsMargins(0, 0, 0, 0)
        document_layout.setSpacing(7)
        self.document_edit = QLineEdit(
            authorization.authorization_document if authorization else ""
        )
        self.document_edit.setPlaceholderText("授权书本地路径（确认授权时必填）")
        document_layout.addWidget(self.document_edit, 1)
        document_browse = button("选择文件…", "ghost")
        document_browse.clicked.connect(self._browse_document)
        document_layout.addWidget(document_browse)
        form.addRow("授权文件", document_row)

        now = service.now()
        start = authorization.start_time if authorization else now
        end = authorization.end_time if authorization else now + timedelta(days=30)
        self.start_edit = QDateTimeEdit(_qdatetime(start))
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("开始时间 *", self.start_edit)
        self.end_edit = QDateTimeEdit(_qdatetime(end))
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        form.addRow("结束时间 *", self.end_edit)

        self.status_combo = QComboBox()
        for label, value in AuthStatus.options():
            self.status_combo.addItem(label, value.value)
        if authorization:
            self.status_combo.setCurrentIndex(
                self.status_combo.findData(authorization.authorization_status.value)
            )
        else:
            self.status_combo.setCurrentIndex(self.status_combo.findData(AuthStatus.PENDING.value))
        form.addRow("授权状态 *", self.status_combo)

        self.notes_edit = QPlainTextEdit(authorization.notes if authorization else "")
        self.notes_edit.setPlaceholderText("测试限制、联系人、允许的时间窗口等。")
        self.notes_edit.setFixedHeight(80)
        form.addRow("备注", self.notes_edit)
        layout.addLayout(form)

        self.error_label = _inline_error(self)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_document(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "选择授权文件",
            self.document_edit.text(),
            "文档 (*.pdf *.png *.jpg *.jpeg *.doc *.docx);;所有文件 (*.*)",
        )
        if selected:
            self.document_edit.setText(selected)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _save(self) -> None:
        source = self.source_edit.text().strip()
        document = self.document_edit.text().strip()
        status = self.status_combo.currentData()
        if not source:
            self._show_error("授权来源不能为空。")
            return
        if status == AuthStatus.CONFIRMED.value and not document:
            self._show_error("“已确认”授权必须填写授权文件路径。")
            return
        start = _read_qdatetime(self.start_edit)
        end = _read_qdatetime(self.end_edit)
        if end <= start:
            self._show_error("结束时间必须晚于开始时间。")
            return
        try:
            if self._authorization is None:
                authorization = self._service.create_authorization(
                    self._project_id,
                    authorization_source=source,
                    authorization_document=document,
                    start_time=start,
                    end_time=end,
                    authorization_status=status,
                    notes=self.notes_edit.toPlainText(),
                )
            else:
                authorization = self._service.update_authorization(
                    self._project_id,
                    self._authorization.authorization_id,
                    authorization_source=source,
                    authorization_document=document,
                    start_time=start,
                    end_time=end,
                    authorization_status=status,
                    notes=self.notes_edit.toPlainText(),
                )
        except AppError as exc:
            self._show_error(str(exc))
            return
        self.saved_authorization = authorization
        self.accept()


class ScopeAssetDialog(QDialog):
    def __init__(
        self,
        scope_service: ScopeAssetService,
        authorization_service: AuthorizationService,
        project_id: int,
        asset: ScopeAsset | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._scope_service = scope_service
        self._authorization_service = authorization_service
        self._project_id = project_id
        self._asset = asset
        self.saved_asset: ScopeAsset | None = None
        self.setWindowTitle("编辑授权资产" if asset else "新增授权资产")
        self.setModal(True)
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 18)
        layout.setSpacing(12)
        title = QLabel("编辑授权资产" if asset else "新增授权资产")
        title.setObjectName("dialogTitle")
        layout.addWidget(title)
        hint = QLabel(
            "远程资产必须精确匹配，不支持通配符、URL、端口或网段；"
            "本地资产与远程资产分开管理。"
        )
        hint.setObjectName("formHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        self.type_combo = QComboBox()
        for label, value in AssetType.options():
            self.type_combo.addItem(label, value.value)
        if asset:
            self.type_combo.setCurrentIndex(self.type_combo.findData(asset.asset_type.value))
        form.addRow("资产类型 *", self.type_combo)

        value_row = QWidget()
        value_layout = QHBoxLayout(value_row)
        value_layout.setContentsMargins(0, 0, 0, 0)
        value_layout.setSpacing(7)
        self.value_edit = QLineEdit(asset.asset_value if asset else "")
        self.value_edit.setPlaceholderText("精确域名，例如 example.com")
        value_layout.addWidget(self.value_edit, 1)
        self.browse_button = button("浏览目录…", "ghost")
        self.browse_button.clicked.connect(self._browse_local)
        value_layout.addWidget(self.browse_button)
        form.addRow("资产值 *", value_row)

        self.auth_row = QWidget()
        auth_layout = QHBoxLayout(self.auth_row)
        auth_layout.setContentsMargins(0, 0, 0, 0)
        self.auth_combo = QComboBox()
        authorizations = authorization_service.list_authorizations(project_id)
        now = authorization_service.now()
        effective = [auth for auth in authorizations if auth.is_effective(now)]
        if not effective:
            self.auth_combo.addItem("无有效授权，请先新增并确认授权", None)
        for auth in effective:
            self.auth_combo.addItem(
                f"#{auth.authorization_id}  {auth.authorization_source}"
                f"  （至 {local_display(auth.end_time)}）",
                auth.authorization_id,
            )
        if asset and asset.authorization_id is not None:
            index = self.auth_combo.findData(asset.authorization_id)
            if index < 0:
                self.auth_combo.addItem(
                    f"#{asset.authorization_id}  当前绑定授权（已失效）",
                    asset.authorization_id,
                )
                index = self.auth_combo.count() - 1
            self.auth_combo.setCurrentIndex(index)
        auth_layout.addWidget(self.auth_combo)
        self.auth_label = QLabel("关联授权 *")
        form.addRow(self.auth_label, self.auth_row)

        self.operations_group = QGroupBox("允许操作（远程资产必须至少选择一项）")
        operations_layout = QHBoxLayout(self.operations_group)
        operations_layout.setContentsMargins(11, 12, 11, 9)
        self.operation_checks: dict[str, object] = {}
        current_operations = asset.allowed_operations if asset else ()
        for label, operation in RemoteOperation.options():
            checkbox = QCheckBox(label)
            checkbox.setChecked(operation.value in current_operations)
            operations_layout.addWidget(checkbox)
            self.operation_checks[operation.value] = checkbox
        operations_layout.addStretch(1)
        form.addRow(self.operations_group)

        self.status_combo = QComboBox()
        for label, value in AssetStatus.options():
            self.status_combo.addItem(label, value.value)
        if asset:
            self.status_combo.setCurrentIndex(self.status_combo.findData(asset.asset_status.value))
        form.addRow("资产状态 *", self.status_combo)

        self.notes_edit = QPlainTextEdit(asset.notes if asset else "")
        self.notes_edit.setFixedHeight(70)
        self.notes_edit.setPlaceholderText("仅记录与授权范围相关的必要说明。")
        form.addRow("备注", self.notes_edit)
        layout.addLayout(form)

        self.error_label = _inline_error(self)
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.type_combo.currentIndexChanged.connect(self._update_type_state)
        self._update_type_state()

    def _is_remote(self) -> bool:
        try:
            return AssetType(str(self.type_combo.currentData())).is_remote
        except ValueError:
            return True

    def _update_type_state(self) -> None:
        remote = self._is_remote()
        self.auth_label.setVisible(remote)
        self.auth_row.setVisible(remote)
        self.operations_group.setVisible(remote)
        self.browse_button.setVisible(not remote)
        if remote:
            self.value_edit.setPlaceholderText("精确域名或 IP，例如 example.com / 203.0.113.10")
        else:
            self.value_edit.setPlaceholderText("本地绝对路径")

    def _browse_local(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "选择授权目录", self.value_edit.text())
        if selected:
            self.value_edit.setText(selected)

    def _show_error(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _save(self) -> None:
        value = self.value_edit.text().strip()
        if not value:
            self._show_error("资产值不能为空。")
            return
        remote = self._is_remote()
        authorization_id = self.auth_combo.currentData() if remote else None
        if remote and authorization_id is None:
            self._show_error("远程资产必须关联一条当前有效的已确认授权。")
            return
        operations = [
            operation
            for operation, checkbox in self.operation_checks.items()
            if checkbox.isChecked()
        ]
        if remote and not operations:
            self._show_error("远程资产必须明确勾选至少一项允许操作。")
            return
        try:
            if self._asset is None:
                asset = self._scope_service.create_asset(
                    self._project_id,
                    asset_type=self.type_combo.currentData(),
                    asset_value=value,
                    authorization_id=authorization_id,
                    allowed_operations=operations if remote else [],
                    asset_status=self.status_combo.currentData(),
                    notes=self.notes_edit.toPlainText(),
                )
            else:
                asset = self._scope_service.update_asset(
                    self._project_id,
                    self._asset.asset_id,
                    asset_type=self.type_combo.currentData(),
                    asset_value=value,
                    authorization_id=authorization_id,
                    allowed_operations=operations if remote else [],
                    asset_status=self.status_combo.currentData(),
                    notes=self.notes_edit.toPlainText(),
                )
        except AppError as exc:
            self._show_error(str(exc))
            return
        self.saved_asset = asset
        self.accept()


class ProjectPage(QWidget):
    projects_changed = Signal()

    def __init__(self, context: AppContext, state: AppState) -> None:
        super().__init__()
        self._context = context
        self._state = state
        self._clock = context.clock
        self._updating = False
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(180)
        self._search_timer.timeout.connect(self.refresh_projects)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)
        layout.addWidget(
            page_header(
                "项目管理",
                "管理授权研究项目、授权记录与精确资产范围。所有判断由后端服务执行。",
                "授权与资产管理",
            )
        )

        context_bar = QFrame()
        context_bar.setObjectName("notice")
        context_layout = QHBoxLayout(context_bar)
        context_layout.setContentsMargins(13, 9, 13, 9)
        self._context_label = QLabel("")
        self._context_label.setStyleSheet("color: #bae6fd;")
        context_layout.addWidget(self._context_label, 1)
        self._context_hint = QLabel("双击项目可设为当前项目")
        self._context_hint.setObjectName("muted")
        context_layout.addWidget(self._context_hint)
        layout.addWidget(context_bar)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_project_list_tab(), "项目列表")
        self.tabs.addTab(self._build_project_detail_tab(), "项目详情")
        self.tabs.addTab(self._build_authorization_tab(), "授权管理")
        self.tabs.addTab(self._build_asset_tab(), "授权资产")
        layout.addWidget(self.tabs, 1)

        self._state.project_changed.connect(self._on_active_project_changed)
        self.refresh_all()

    # ------------------------------------------------------------------ UI build
    def _build_project_list_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        toolbar = QHBoxLayout()
        toolbar.setSpacing(8)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索项目名称、说明或本地路径")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.setFixedWidth(270)
        self.search_edit.textChanged.connect(lambda: self._search_timer.start())
        toolbar.addWidget(self.search_edit)

        self.status_filter = QComboBox()
        self.status_filter.addItem("全部状态", None)
        for label, value in ProjectStatus.options():
            self.status_filter.addItem(label, value.value)
        self.status_filter.currentIndexChanged.connect(self.refresh_projects)
        toolbar.addWidget(self.status_filter)

        self.sort_combo = QComboBox()
        self.sort_combo.addItem("创建时间：最新优先", True)
        self.sort_combo.addItem("创建时间：最早优先", False)
        self.sort_combo.currentIndexChanged.connect(self.refresh_projects)
        toolbar.addWidget(self.sort_combo)
        toolbar.addStretch(1)

        self.new_project_button = button("新建项目", "primary")
        self.new_project_button.clicked.connect(self._new_project)
        toolbar.addWidget(self.new_project_button)
        self.edit_project_button = button("编辑")
        self.edit_project_button.clicked.connect(self._edit_project)
        toolbar.addWidget(self.edit_project_button)
        self.delete_project_button = button("删除", "danger")
        self.delete_project_button.clicked.connect(self._delete_project)
        toolbar.addWidget(self.delete_project_button)
        self.activate_button = button("设为当前")
        self.activate_button.clicked.connect(self._set_active)
        toolbar.addWidget(self.activate_button)
        layout.addLayout(toolbar)

        self.project_table = configure_table(
            ["ID", "项目名称", "类型", "状态", "本地路径", "创建时间", "更新时间", "当前"]
        )
        self.project_table.itemSelectionChanged.connect(self._project_selection_changed)
        self.project_table.doubleClicked.connect(lambda _index: self._set_active())
        layout.addWidget(self.project_table, 1)

        footer = QHBoxLayout()
        self.project_count_label = QLabel("")
        self.project_count_label.setObjectName("muted")
        footer.addWidget(self.project_count_label)
        footer.addStretch(1)
        footer_hint = QLabel("名称本身不等于授权；远程资产另需有效授权。")
        footer_hint.setObjectName("muted")
        footer.addWidget(footer_hint)
        layout.addLayout(footer)
        return page

    def _build_project_detail_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 14)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel("项目详情")
        title.setObjectName("sectionTitle")
        top.addWidget(title)
        top.addStretch(1)
        self.detail_active_pill = QLabel("未选择")
        self.detail_active_pill.setObjectName("pill")
        self.detail_active_pill.setProperty("level", "muted")
        top.addWidget(self.detail_active_pill)
        edit = button("编辑项目")
        edit.clicked.connect(self._edit_project)
        top.addWidget(edit)
        layout.addLayout(top)

        card = QFrame()
        card.setObjectName("card")
        grid = QGridLayout(card)
        grid.setContentsMargins(20, 18, 20, 18)
        grid.setHorizontalSpacing(26)
        grid.setVerticalSpacing(12)
        self._detail_values: dict[str, QLabel] = {}
        fields = [
            ("project_name", "项目名称"),
            ("project_id", "项目 ID"),
            ("project_type", "项目类型"),
            ("status", "项目状态"),
            ("local_path", "本地路径"),
            ("created_at", "创建时间"),
            ("updated_at", "更新时间"),
            ("description", "项目说明"),
        ]
        for index, (key, label) in enumerate(fields):
            row = index // 2
            column = (index % 2) * 2
            name = QLabel(label)
            name.setObjectName("muted")
            value = QLabel("—")
            value.setWordWrap(True)
            value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            grid.addWidget(name, row, column)
            grid.addWidget(value, row, column + 1)
            self._detail_values[key] = value
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout.addWidget(card)

        summary_card = QFrame()
        summary_card.setObjectName("card")
        summary_layout = QHBoxLayout(summary_card)
        summary_layout.setContentsMargins(20, 14, 20, 14)
        summary_layout.setSpacing(28)
        self.detail_auth_summary = QLabel("授权记录：—")
        self.detail_asset_summary = QLabel("授权资产：—")
        summary_layout.addWidget(self.detail_auth_summary)
        summary_layout.addWidget(self.detail_asset_summary)
        summary_layout.addStretch(1)
        self.detail_activate_button = button("设为当前项目", "primary")
        self.detail_activate_button.clicked.connect(self._set_active)
        summary_layout.addWidget(self.detail_activate_button)
        layout.addWidget(summary_card)
        layout.addStretch(1)
        return page

    def _build_authorization_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.auth_context_label = QLabel("")
        self.auth_context_label.setObjectName("sectionTitle")
        top.addWidget(self.auth_context_label)
        top.addStretch(1)
        self.new_auth_button = button("新增授权", "primary")
        self.new_auth_button.clicked.connect(self._new_authorization)
        top.addWidget(self.new_auth_button)
        self.edit_auth_button = button("编辑")
        self.edit_auth_button.clicked.connect(self._edit_authorization)
        top.addWidget(self.edit_auth_button)
        self.revoke_auth_button = button("撤销")
        self.revoke_auth_button.clicked.connect(self._revoke_authorization)
        top.addWidget(self.revoke_auth_button)
        self.delete_auth_button = button("删除", "danger")
        self.delete_auth_button.clicked.connect(self._delete_authorization)
        top.addWidget(self.delete_auth_button)
        layout.addLayout(top)

        self.auth_alert = QLabel("")
        self.auth_alert.setWordWrap(True)
        self.auth_alert.setStyleSheet(
            "color: #fcd34d; background: #2c210d; border: 1px solid #6b4e0b;"
            "border-radius: 8px; padding: 8px;"
        )
        self.auth_alert.hide()
        layout.addWidget(self.auth_alert)

        self.auth_table = configure_table(
            ["ID", "授权来源", "授权文件", "开始时间", "结束时间", "状态", "当前有效性", "备注"]
        )
        self.auth_table.itemSelectionChanged.connect(self._update_authorization_history)
        self.auth_table.doubleClicked.connect(lambda _index: self._edit_authorization())
        layout.addWidget(self.auth_table, 2)

        history_header = QHBoxLayout()
        self.history_title = QLabel("授权变更历史")
        self.history_title.setObjectName("sectionTitle")
        history_header.addWidget(self.history_title)
        history_header.addStretch(1)
        self.history_hint = QLabel("选择一条授权记录查看")
        self.history_hint.setObjectName("muted")
        history_header.addWidget(self.history_hint)
        layout.addLayout(history_header)
        self.auth_history_table = configure_table(["时间", "动作", "变更摘要"])
        self.auth_history_table.setMaximumHeight(190)
        layout.addWidget(self.auth_history_table, 1)
        return page

    def _build_asset_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        self.asset_context_label = QLabel("")
        self.asset_context_label.setObjectName("sectionTitle")
        top.addWidget(self.asset_context_label)
        top.addStretch(1)
        self.new_asset_button = button("新增资产", "primary")
        self.new_asset_button.clicked.connect(self._new_asset)
        top.addWidget(self.new_asset_button)
        self.edit_asset_button = button("编辑")
        self.edit_asset_button.clicked.connect(self._edit_asset)
        top.addWidget(self.edit_asset_button)
        self.delete_asset_button = button("删除", "danger")
        self.delete_asset_button.clicked.connect(self._delete_asset)
        top.addWidget(self.delete_asset_button)
        layout.addLayout(top)

        self.asset_alert = QLabel("")
        self.asset_alert.setWordWrap(True)
        self.asset_alert.setStyleSheet(
            "color: #fca5a5; background: #2d1417; border: 1px solid #6e2a30;"
            "border-radius: 8px; padding: 8px;"
        )
        self.asset_alert.hide()
        layout.addWidget(self.asset_alert)

        self.asset_table = configure_table(
            ["ID", "类型", "资产值", "关联授权", "允许操作", "状态", "备注"]
        )
        self.asset_table.itemSelectionChanged.connect(self._update_asset_buttons)
        self.asset_table.doubleClicked.connect(lambda _index: self._edit_asset())
        layout.addWidget(self.asset_table, 1)

        footer = QHBoxLayout()
        hint = QLabel(
            "远程资产只能精确绑定当前有效的已确认授权；本地资产不绑定远程授权，"
            "后续扫描器仍需执行本地范围校验。"
        )
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        footer.addWidget(hint, 1)
        layout.addLayout(footer)
        return page

    # ------------------------------------------------------------------ refresh
    def refresh_all(self) -> None:
        self._update_context()
        self.refresh_projects()
        self.refresh_authorizations()
        self.refresh_assets()

    def _update_context(self) -> None:
        current = self._state.current_project
        if current:
            text = f"当前项目：#{current.project_id}  {current.project_name}  ·  {current.type_label}"
        else:
            text = "当前未选择活动项目。授权和资产子页需要先设置当前项目。"
        self._context_label.setText(text)
        self.auth_context_label.setText(f"授权管理 · {current.project_name}" if current else "授权管理")
        self.asset_context_label.setText(
            f"授权资产 · {current.project_name}" if current else "授权资产"
        )

    def refresh_projects(self) -> None:
        if self._updating:
            return
        self._updating = True
        try:
            selected = selected_id(self.project_table)
            if selected is None and self._state.current_project_id is not None:
                selected = self._state.current_project_id
            projects = self._context.project_service.list_projects(
                search=self.search_edit.text(),
                status=self.status_filter.currentData(),
                newest_first=bool(self.sort_combo.currentData()),
            )
            self.project_table.setRowCount(0)
            active_id = self._state.current_project_id
            selected_row = -1
            for row_index, project in enumerate(projects):
                self.project_table.insertRow(row_index)
                values = [
                    table_item(str(project.project_id), data=project.project_id),
                    table_item(project.project_name),
                    table_item(project.type_label),
                    table_item(
                        project.status_label, color=status_color(project.status_label)
                    ),
                    table_item(project.local_path or "—"),
                    table_item(local_display(project.created_at)),
                    table_item(local_display(project.updated_at)),
                    table_item("是" if project.project_id == active_id else ""),
                ]
                for column, item in enumerate(values):
                    self.project_table.setItem(row_index, column, item)
                if project.project_id == selected:
                    selected_row = row_index
            header = self.project_table.horizontalHeader()
            for column, width in enumerate([50, 200, 112, 78, 220, 146, 146]):
                header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
                self.project_table.setColumnWidth(column, width)
            header.setStretchLastSection(True)
            if projects:
                if selected_row < 0:
                    selected_row = 0
                self.project_table.selectRow(selected_row)
            self.project_count_label.setText(f"共 {len(projects)} 个项目")
            self._update_project_buttons()
        except Exception as exc:
            show_error(self, exc, "读取项目失败")
        finally:
            self._updating = False
        if self.project_table.currentRow() >= 0:
            self._project_selection_changed()

    def _project_selection_changed(self) -> None:
        project_id = selected_id(self.project_table)
        if project_id is None:
            self._clear_detail()
            self._update_project_buttons()
            return
        try:
            project = self._context.project_service.get_project(project_id)
            auth_count = len(self._context.authorization_service.list_authorizations(project_id))
            asset_count = self._context.scope_service.count_assets(project_id)
        except Exception as exc:
            show_error(self, exc, "读取项目详情失败")
            return
        active = self._state.current_project_id == project.project_id
        values = {
            "project_name": project.project_name,
            "project_id": f"#{project.project_id}",
            "project_type": project.type_label,
            "status": project.status_label,
            "local_path": project.local_path or "—",
            "created_at": local_display(project.created_at),
            "updated_at": local_display(project.updated_at),
            "description": project.description or "—",
        }
        for key, value in values.items():
            self._detail_values[key].setText(value)
        self._detail_values["status"].setStyleSheet(
            f"color: {status_color(project.status_label)};"
        )
        self.detail_active_pill.setText("当前项目" if active else "非当前项目")
        self.detail_active_pill.setProperty("level", "success" if active else "muted")
        self.detail_active_pill.style().unpolish(self.detail_active_pill)
        self.detail_active_pill.style().polish(self.detail_active_pill)
        self.detail_auth_summary.setText(f"授权记录：{auth_count}")
        self.detail_asset_summary.setText(f"授权资产：{asset_count}")
        self._update_project_buttons()

    def _clear_detail(self) -> None:
        for label in self._detail_values.values():
            label.setText("—")
        self.detail_active_pill.setText("未选择")
        self.detail_active_pill.setProperty("level", "muted")
        self.detail_auth_summary.setText("授权记录：—")
        self.detail_asset_summary.setText("授权资产：—")

    def _update_project_buttons(self) -> None:
        has_selection = selected_id(self.project_table) is not None
        self.edit_project_button.setEnabled(has_selection)
        self.delete_project_button.setEnabled(has_selection)
        self.activate_button.setEnabled(has_selection)
        self.detail_activate_button.setEnabled(has_selection)

    def refresh_authorizations(self) -> None:
        current = self._state.current_project
        if current is None:
            self.auth_table.setRowCount(0)
            self.auth_history_table.setRowCount(0)
            self.auth_alert.hide()
            self._set_auth_buttons(False)
            self.history_hint.setText("请先设置当前活动项目")
            return
        try:
            records = self._context.authorization_service.list_authorizations(
                current.project_id
            )
        except Exception as exc:
            show_error(self, exc, "读取授权失败")
            return
        selected_auth = selected_id(self.auth_table)
        self.auth_table.setRowCount(0)
        invalid_count = 0
        expiring_count = 0
        now = self._clock()
        for row_index, auth in enumerate(records):
            validity = auth.validity_label(now)
            if not auth.is_effective(now):
                invalid_count += 1
            elif auth.end_time <= now + timedelta(days=7):
                expiring_count += 1
            self.auth_table.insertRow(row_index)
            values = [
                table_item(str(auth.authorization_id), data=auth.authorization_id),
                table_item(auth.authorization_source),
                table_item(auth.authorization_document or "—"),
                table_item(local_display(auth.start_time)),
                table_item(local_display(auth.end_time)),
                table_item(auth.status_label, color=status_color(auth.status_label)),
                table_item(validity, color=status_color(validity)),
                table_item(auth.notes or "—"),
            ]
            for column, item in enumerate(values):
                if not auth.is_effective(now):
                    item.setBackground(QBrush(QColor("#1f1418")))
                self.auth_table.setItem(row_index, column, item)
        auth_header = self.auth_table.horizontalHeader()
        for column, width in enumerate([50, 185, 160, 146, 146, 80, 88]):
            auth_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.auth_table.setColumnWidth(column, width)
        auth_header.setStretchLastSection(True)
        self._set_auth_buttons(True)
        if records:
            target_row = 0
            for index, auth in enumerate(records):
                if auth.authorization_id == selected_auth:
                    target_row = index
                    break
            self.auth_table.selectRow(target_row)
        if invalid_count:
            self.auth_alert.setText(
                f"注意：{invalid_count} 条授权当前无效（过期、撤销、待审核或未生效）。"
                "无效授权不能用于远程检测。"
            )
            self.auth_alert.show()
        elif expiring_count:
            self.auth_alert.setText(f"提示：{expiring_count} 条有效授权将在 7 天内到期。")
            self.auth_alert.show()
        else:
            self.auth_alert.hide()
        self.auth_context_label.setText(
            f"授权管理 · {current.project_name}（{len(records)} 条）"
        )
        self._update_authorization_history()

    def _selected_authorization(self) -> Authorization | None:
        current = self._state.current_project
        auth_id = selected_id(self.auth_table)
        if current is None or auth_id is None:
            return None
        try:
            return self._context.authorization_service.get_authorization(
                current.project_id, auth_id
            )
        except NotFoundError:
            return None

    def _update_authorization_history(self) -> None:
        auth = self._selected_authorization()
        self.auth_history_table.setRowCount(0)
        if auth is None:
            self.history_hint.setText("选择一条授权记录查看")
            return
        try:
            history = self._context.authorization_service.list_history(
                auth.project_id, auth.authorization_id
            )
        except Exception as exc:
            show_error(self, exc, "读取授权历史失败")
            return
        action_labels = {
            "created": "新增",
            "updated": "修改",
            "revoked": "撤销",
            "expired": "到期",
            "deleted": "删除",
        }
        for row_index, item in enumerate(history):
            self.auth_history_table.insertRow(row_index)
            self.auth_history_table.setItem(
                row_index, 0, table_item(local_display(item.created_at, with_seconds=True))
            )
            self.auth_history_table.setItem(
                row_index, 1, table_item(action_labels.get(item.action, item.action))
            )
            self.auth_history_table.setItem(
                row_index, 2, table_item(item.change_summary)
            )
        history_header = self.auth_history_table.horizontalHeader()
        history_header.setStretchLastSection(True)
        history_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.auth_history_table.setColumnWidth(0, 185)
        history_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.auth_history_table.setColumnWidth(1, 85)
        self.history_hint.setText(f"授权 #{auth.authorization_id} · {len(history)} 条变更")
        self._set_auth_buttons(True)

    def _set_auth_buttons(self, enabled: bool) -> None:
        self.new_auth_button.setEnabled(enabled)
        selected = enabled and selected_id(self.auth_table) is not None
        self.edit_auth_button.setEnabled(selected)
        self.delete_auth_button.setEnabled(selected)
        self.revoke_auth_button.setEnabled(selected)

    def refresh_assets(self) -> None:
        current = self._state.current_project
        if current is None:
            self.asset_table.setRowCount(0)
            self.asset_alert.hide()
            self._set_asset_buttons(False)
            return
        try:
            assets = self._context.scope_service.list_assets(current.project_id)
            authorizations = {
                auth.authorization_id: auth
                for auth in self._context.authorization_service.list_authorizations(
                    current.project_id
                )
            }
        except Exception as exc:
            show_error(self, exc, "读取授权资产失败")
            return
        self.asset_table.setRowCount(0)
        expired_auth_assets = 0
        for row_index, asset in enumerate(assets):
            auth = (
                authorizations.get(asset.authorization_id)
                if asset.authorization_id is not None
                else None
            )
            if asset.is_remote and (auth is None or not auth.is_effective(self._clock())):
                expired_auth_assets += 1
            auth_text = "本地资产" if not asset.is_remote else (
                f"#{auth.authorization_id} {auth.authorization_source}" if auth else "授权缺失"
            )
            self.asset_table.insertRow(row_index)
            values = [
                table_item(str(asset.asset_id), data=asset.asset_id),
                table_item(asset.type_label),
                table_item(asset.asset_value),
                table_item(auth_text),
                table_item(self._context.scope_service.operations_display(asset)),
                table_item(asset.status_label, color=status_color(asset.status_label)),
                table_item(asset.notes or "—"),
            ]
            for column, item in enumerate(values):
                self.asset_table.setItem(row_index, column, item)
        asset_header = self.asset_table.horizontalHeader()
        for column, width in enumerate([50, 110, 240, 200, 165, 72]):
            asset_header.setSectionResizeMode(column, QHeaderView.ResizeMode.Fixed)
            self.asset_table.setColumnWidth(column, width)
        asset_header.setStretchLastSection(True)
        self._set_asset_buttons(True)
        if expired_auth_assets:
            self.asset_alert.setText(
                f"注意：{expired_auth_assets} 个远程资产关联的授权已无效。"
                "后端会拒绝这些目标的远程操作，请更新授权或停用资产。"
            )
            self.asset_alert.show()
        else:
            self.asset_alert.hide()
        self.asset_context_label.setText(
            f"授权资产 · {current.project_name}（{len(assets)} 个）"
        )

    def _update_asset_buttons(self) -> None:
        selected = selected_id(self.asset_table) is not None
        self.edit_asset_button.setEnabled(selected)
        self.delete_asset_button.setEnabled(selected)

    def _set_asset_buttons(self, enabled: bool) -> None:
        self.new_asset_button.setEnabled(enabled)
        self.edit_asset_button.setEnabled(enabled and selected_id(self.asset_table) is not None)
        self.delete_asset_button.setEnabled(enabled and selected_id(self.asset_table) is not None)

    # ------------------------------------------------------------------ actions
    def _new_project(self) -> None:
        dialog = ProjectDialog(self._context.project_service, parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._state.notify_projects_changed()
            self.refresh_all()
            self.projects_changed.emit()

    def _edit_project(self) -> None:
        project_id = selected_id(self.project_table)
        if project_id is None:
            return
        try:
            project = self._context.project_service.get_project(project_id)
        except Exception as exc:
            show_error(self, exc, "读取项目失败")
            return
        dialog = ProjectDialog(self._context.project_service, project, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self._state.notify_projects_changed()
            self.refresh_all()
            self.projects_changed.emit()

    def _delete_project(self) -> None:
        project_id = selected_id(self.project_table)
        if project_id is None:
            return
        try:
            project = self._context.project_service.get_project(project_id)
        except Exception as exc:
            show_error(self, exc, "读取项目失败")
            return
        if not confirm(
            self,
            "删除项目",
            f"确定删除项目“{project.project_name}”吗？\n\n"
            "该项目的授权、授权资产和授权历史将被级联删除；审计日志会保留。此操作不可撤销。",
            dangerous=True,
        ):
            return
        try:
            self._context.project_service.delete_project(project_id)
        except Exception as exc:
            show_error(self, exc, "删除项目失败")
            return
        self._state.notify_projects_changed()
        self.refresh_all()
        self.projects_changed.emit()

    def _set_active(self) -> None:
        project_id = selected_id(self.project_table)
        if project_id is None:
            return
        try:
            self._state.set_active_project(project_id)
        except Exception as exc:
            show_error(self, exc, "设置活动项目失败")
            return
        self.refresh_all()

    def _new_authorization(self) -> None:
        current = self._state.current_project
        if current is None:
            QMessageBox.information(self, "未选择项目", "请先设置当前活动项目。")
            return
        dialog = AuthorizationDialog(
            self._context.authorization_service, current.project_id, parent=self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_authorizations()
            self.refresh_assets()

    def _edit_authorization(self) -> None:
        auth = self._selected_authorization()
        if auth is None:
            return
        if auth.authorization_status is AuthStatus.REVOKED:
            QMessageBox.information(self, "不可修改", "已撤销授权不可修改；如需重新授权，请新增记录。")
            return
        dialog = AuthorizationDialog(
            self._context.authorization_service, auth.project_id, auth, self
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_authorizations()
            self.refresh_assets()

    def _revoke_authorization(self) -> None:
        auth = self._selected_authorization()
        if auth is None:
            return
        if auth.authorization_status is AuthStatus.REVOKED:
            QMessageBox.information(self, "已撤销", "该授权已经撤销。")
            return
        if not confirm(
            self,
            "撤销授权",
            f"确定撤销授权 #{auth.authorization_id} 吗？\n\n"
            "撤销后立即禁止该授权支撑的远程检测。该操作会记录变更历史。",
            dangerous=True,
        ):
            return
        try:
            self._context.authorization_service.revoke_authorization(
                auth.project_id, auth.authorization_id
            )
        except Exception as exc:
            show_error(self, exc, "撤销授权失败")
            return
        self.refresh_authorizations()
        self.refresh_assets()

    def _delete_authorization(self) -> None:
        auth = self._selected_authorization()
        if auth is None:
            return
        if not confirm(
            self,
            "删除授权",
            f"确定删除授权 #{auth.authorization_id} 吗？\n\n"
            "删除会永久移除记录。仍有关联资产时会被后端拒绝。",
            dangerous=True,
        ):
            return
        try:
            self._context.authorization_service.delete_authorization(
                auth.project_id, auth.authorization_id
            )
        except ConflictError as exc:
            show_error(self, exc, "无法删除授权")
            return
        except Exception as exc:
            show_error(self, exc, "删除授权失败")
            return
        self.refresh_authorizations()
        self.refresh_assets()

    def _new_asset(self) -> None:
        current = self._state.current_project
        if current is None:
            QMessageBox.information(self, "未选择项目", "请先设置当前活动项目。")
            return
        dialog = ScopeAssetDialog(
            self._context.scope_service,
            self._context.authorization_service,
            current.project_id,
            parent=self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_assets()
            self.refresh_authorizations()

    def _selected_asset(self) -> ScopeAsset | None:
        current = self._state.current_project
        asset_id = selected_id(self.asset_table)
        if current is None or asset_id is None:
            return None
        try:
            return self._context.scope_service.get_asset(current.project_id, asset_id)
        except NotFoundError:
            return None

    def _edit_asset(self) -> None:
        asset = self._selected_asset()
        current = self._state.current_project
        if asset is None or current is None:
            return
        dialog = ScopeAssetDialog(
            self._context.scope_service,
            self._context.authorization_service,
            current.project_id,
            asset,
            self,
        )
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.refresh_assets()

    def _delete_asset(self) -> None:
        asset = self._selected_asset()
        if asset is None:
            return
        if not confirm(
            self,
            "删除授权资产",
            f"确定删除资产“{asset.asset_value}”吗？\n\n"
            "删除后，该目标不再处于授权范围，后端将拒绝相关操作。",
            dangerous=True,
        ):
            return
        try:
            self._context.scope_service.delete_asset(asset.project_id, asset.asset_id)
        except Exception as exc:
            show_error(self, exc, "删除授权资产失败")
            return
        self.refresh_assets()
        self.refresh_authorizations()

    def _on_active_project_changed(self, project) -> None:
        self._update_context()
        self.refresh_projects()
        self.refresh_authorizations()
        self.refresh_assets()
