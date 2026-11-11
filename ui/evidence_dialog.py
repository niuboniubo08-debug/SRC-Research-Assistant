"""Add-evidence dialog used by both management pages."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.bootstrap import AppContext
from core.models import Evidence, EvidenceType, Finding
from services.evidence_service import SENSITIVE_WARNING
from ui.widgets import button, notice_frame


class EvidenceAddWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        service,
        *,
        project_id: int,
        finding_id: int,
        evidence_type: EvidenceType,
        title: str,
        description: str,
        source_path: str | None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._service = service
        self._kwargs = {
            "project_id": project_id,
            "finding_id": finding_id,
            "evidence_type": evidence_type,
            "title": title,
            "description": description,
            "source_path": source_path,
        }

    def run(self) -> None:
        try:
            evidence = self._service.add_evidence(**self._kwargs)
        except Exception as exc:  # noqa: BLE001 - delivered through Qt
            self.failed.emit(str(exc))
            return
        self.completed.emit(evidence)


class EvidenceDialog(QDialog):
    def __init__(
        self,
        context: AppContext,
        *,
        finding: Finding | None = None,
        initial_project_id: int | None = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._context = context
        self._service = context.evidence_service
        self._fixed_finding = finding
        self._initial_project_id = initial_project_id
        self._worker: EvidenceAddWorker | None = None
        self.created_evidence: Evidence | None = None
        self.setWindowTitle("添加证据")
        self.setMinimumWidth(620)
        self._build()
        self._fill_projects()
        self._load_findings()
        if finding is not None:
            self._select_fixed_finding(finding)

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 16)
        layout.setSpacing(10)
        layout.addWidget(notice_frame(SENSITIVE_WARNING, "warning"))

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(9)
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._load_findings)
        form.addRow("所属项目", self.project_combo)
        self.finding_combo = QComboBox()
        self.finding_combo.currentIndexChanged.connect(self._update_save)
        form.addRow("关联漏洞", self.finding_combo)
        self.type_combo = QComboBox()
        for label, value in EvidenceType.options():
            self.type_combo.addItem(label, value.value)
        self.type_combo.currentIndexChanged.connect(self._type_changed)
        form.addRow("证据类型", self.type_combo)
        self.title_edit = QLineEdit()
        self.title_edit.setMaxLength(200)
        self.title_edit.setPlaceholderText("例如：依赖漏洞复现截图")
        self.title_edit.textChanged.connect(self._update_save)
        form.addRow("标题", self.title_edit)
        self.description_edit = QPlainTextEdit()
        self.description_edit.setPlaceholderText(
            "粘贴已脱敏的代码片段、扫描结果摘要或人工说明；不要放入密钥。"
        )
        self.description_edit.setMinimumHeight(130)
        form.addRow("说明 / 内容", self.description_edit)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("必须位于当前项目授权根目录内")
        self.file_edit.textChanged.connect(self._update_save)
        self.file_button = button("选择文件")
        self.file_button.clicked.connect(self._browse_file)
        file_row = QWidget()
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(6)
        file_layout.addWidget(self.file_edit, 1)
        file_layout.addWidget(self.file_button)
        self.file_row = file_row
        form.addRow("本地文件", file_row)
        layout.addLayout(form)

        self.confirm_check = QCheckBox(
            "我已人工确认证据不包含未脱敏密钥、凭据或无关个人信息"
        )
        self.confirm_check.toggled.connect(self._update_save)
        layout.addWidget(self.confirm_check)
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet("color: #fca5a5;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        footer = QHBoxLayout()
        footer.addStretch(1)
        cancel = button("取消", "ghost")
        cancel.clicked.connect(self.reject)
        footer.addWidget(cancel)
        self.save_button = button("保存证据", "primary")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self._save)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self._type_changed()

    def _fill_projects(self) -> None:
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        for project in self._context.project_service.list_projects():
            self.project_combo.addItem(
                f"#{project.project_id}  {project.project_name}", project.project_id
            )
        self.project_combo.blockSignals(False)
        target_id = self._initial_project_id
        if target_id is None and self._fixed_finding is not None:
            target_id = self._fixed_finding.project_id
        if target_id is None:
            active_id = getattr(self.parent(), "_state", None)
            if active_id is not None:
                try:
                    target_id = active_id.current_project_id
                except Exception:
                    target_id = None
        index = self.project_combo.findData(target_id)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)

    def _select_fixed_finding(self, finding: Finding) -> None:
        index = self.project_combo.findData(finding.project_id)
        if index >= 0:
            self.project_combo.setCurrentIndex(index)
        self.finding_combo.clear()
        self.finding_combo.addItem(
            f"{finding.severity_label} · {finding.title}"[:180], finding.finding_id
        )
        self.finding_combo.setCurrentIndex(0)
        self.project_combo.setEnabled(False)
        self.finding_combo.setEnabled(False)
        self.title_edit.setText(f"证据：{finding.title}"[:200])
        if not self.description_edit.toPlainText():
            self.description_edit.setPlainText(self._finding_prefill(finding))
        self._update_save()

    def _load_findings(self) -> None:
        if self._fixed_finding is not None:
            return
        self.finding_combo.clear()
        project_id = self.project_combo.currentData()
        if project_id is None:
            return
        try:
            findings = self._context.vulnerability_service.list_findings(
                project_id=int(project_id), limit=1000
            )
        except Exception as exc:
            self.error_label.setText(str(exc))
            self.error_label.show()
            return
        for finding in findings:
            self.finding_combo.addItem(
                f"{finding.severity_label} · {finding.title}"[:180],
                finding.finding_id,
            )
        self._update_save()

    def _type_changed(self) -> None:
        try:
            kind = EvidenceType(str(self.type_combo.currentData()))
        except ValueError:
            kind = EvidenceType.OTHER_FILE
        requires_file = kind.requires_file
        self.file_row.setVisible(requires_file)
        self.description_edit.setPlaceholderText(
            "本地文件证据可填写已脱敏的说明；不会执行文件。"
            if requires_file
            else "粘贴已脱敏的代码片段、扫描结果摘要、依赖信息或人工说明。"
        )
        if not requires_file:
            self.file_edit.clear()
        self._update_save()

    def _browse_file(self) -> None:
        project_id = self.project_combo.currentData()
        start = ""
        if project_id is not None:
            try:
                project = self._context.project_service.get_project(int(project_id))
                start = project.local_path
            except Exception:
                start = ""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "选择项目内证据文件",
            start,
            "证据文件 (*.png *.jpg *.jpeg *.webp *.txt *.log *.json *.md);;所有文件 (*)",
        )
        if path:
            self.file_edit.setText(path)
            if not self.title_edit.text().strip():
                self.title_edit.setText(Path(path).name[:200])
        self._update_save()

    def _finding_prefill(self, finding: Finding) -> str:
        metadata = finding.metadata
        if finding.scanner_name == "pip-audit":
            dependency = metadata.get("dependency_name", "—")
            version = metadata.get("current_version", "—")
            fixes = metadata.get("fix_versions") or []
            return (
                f"依赖：{dependency} {version}\n"
                f"漏洞编号：{finding.rule_id}\n"
                f"修复版本：{', '.join(str(item) for item in fixes) if fixes else '—'}\n"
                f"来源：{metadata.get('source', 'pip-audit')}\n"
            )
        return (
            f"文件：{finding.file_path or '—'}\n"
            f"行号：{finding.line_number or '—'}\n"
            f"规则：{finding.rule_id or '—'}\n"
        )

    def _update_save(self) -> None:
        project_id = self.project_combo.currentData()
        finding_id = self.finding_combo.currentData()
        kind = EvidenceType.from_external(str(self.type_combo.currentData()))
        has_file = bool(self.file_edit.text().strip())
        valid = (
            project_id is not None
            and finding_id is not None
            and self.title_edit.text().strip() != ""
            and self.confirm_check.isChecked()
            and (has_file if kind.requires_file else True)
            and self._worker is None
        )
        self.save_button.setEnabled(valid)

    def _save(self) -> None:
        if self._worker is not None:
            return
        project_id = self.project_combo.currentData()
        finding_id = self.finding_combo.currentData()
        if project_id is None or finding_id is None:
            return
        try:
            kind = EvidenceType(str(self.type_combo.currentData()))
        except ValueError:
            self.error_label.setText("证据类型无效")
            self.error_label.show()
            return
        if not self.confirm_check.isChecked():
            return
        if kind.requires_file and not self.file_edit.text().strip():
            self.error_label.setText("请选择项目内的证据文件")
            self.error_label.show()
            return
        self.error_label.hide()
        self.save_button.setEnabled(False)
        self.project_combo.setEnabled(False)
        self.finding_combo.setEnabled(False)
        self.type_combo.setEnabled(False)
        self.title_edit.setEnabled(False)
        self.description_edit.setEnabled(False)
        self.file_edit.setEnabled(False)
        self.file_button.setEnabled(False)
        worker = EvidenceAddWorker(
            self._service,
            project_id=int(project_id),
            finding_id=int(finding_id),
            evidence_type=kind,
            title=self.title_edit.text(),
            description=self.description_edit.toPlainText(),
            source_path=self.file_edit.text().strip() or None,
            parent=self,
        )
        worker.completed.connect(self._on_added)
        worker.failed.connect(self._on_failed)
        worker.finished.connect(self._on_finished)
        self._worker = worker
        worker.start()

    def _on_added(self, evidence: Evidence) -> None:
        self.created_evidence = evidence
        self.accept()

    def _on_failed(self, message: str) -> None:
        self.error_label.setText(message)
        self.error_label.show()

    def _on_finished(self) -> None:
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        if self.result() != QDialog.DialogCode.Accepted:
            self.project_combo.setEnabled(self._fixed_finding is None)
            self.finding_combo.setEnabled(self._fixed_finding is None)
            self.type_combo.setEnabled(True)
            self.title_edit.setEnabled(True)
            self.description_edit.setEnabled(True)
            self.file_edit.setEnabled(True)
            self.file_button.setEnabled(True)
            self._update_save()

    def closeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        if self._worker is not None and self._worker.isRunning():
            self._worker.requestInterruption()
            self._worker.wait(10000)
        super().closeEvent(event)
