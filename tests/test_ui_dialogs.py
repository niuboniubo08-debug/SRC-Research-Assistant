from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QDialog

from ui.project_page import AuthorizationDialog, ProjectDialog, ScopeAssetDialog


def test_project_dialog_creates_real_project(qtbot, projects, tmp_path: Path) -> None:
    source = tmp_path / "dialog-source"
    source.mkdir()
    dialog = ProjectDialog(projects)
    qtbot.addWidget(dialog)
    dialog.name_edit.setText("对话框验收项目")
    dialog.type_combo.setCurrentIndex(dialog.type_combo.findData("local_audit"))
    dialog.path_edit.setText(str(source))
    dialog.description_edit.setPlainText("由 Qt 对话框实际创建")
    dialog._save()  # noqa: SLF001 - exercise the exact form save handler

    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.saved_project is not None
    stored = projects.get_project(dialog.saved_project.project_id)
    assert stored.project_name == "对话框验收项目"
    assert stored.local_path == str(source)


def test_authorization_dialog_creates_confirmed_record(
    qtbot, authorizations, project, tmp_path: Path
) -> None:
    document = tmp_path / "authorization.pdf"
    document.write_text("local test", encoding="utf-8")
    dialog = AuthorizationDialog(authorizations, project.project_id)
    qtbot.addWidget(dialog)
    dialog.source_edit.setText("对话框授权来源")
    dialog.document_edit.setText(str(document))
    dialog.status_combo.setCurrentIndex(
        dialog.status_combo.findData("confirmed")
    )
    dialog.start_edit.setDateTime(dialog.start_edit.dateTime().addDays(-1))
    dialog.end_edit.setDateTime(dialog.end_edit.dateTime().addDays(30))
    dialog._save()  # noqa: SLF001

    assert dialog.result() == QDialog.DialogCode.Accepted
    created = dialog.saved_authorization
    assert created is not None
    stored = authorizations.get_authorization(project.project_id, created.authorization_id)
    assert stored.authorization_status.value == "confirmed"
    assert stored.authorization_source == "对话框授权来源"


def test_scope_asset_dialog_rejects_missing_operation_and_saves_valid_asset(
    qtbot, scopes, authorizations, project, confirmed_auth
) -> None:
    dialog = ScopeAssetDialog(
        scopes,
        authorizations,
        project.project_id,
    )
    qtbot.addWidget(dialog)
    dialog.value_edit.setText("dialog.example.test")
    # Remote asset without an explicit operation must stay open with validation.
    dialog._save()  # noqa: SLF001
    assert dialog.result() != QDialog.DialogCode.Accepted
    assert "必须明确勾选" in dialog.error_label.text()

    dialog.operation_checks["config_check"].setChecked(True)
    dialog._save()  # noqa: SLF001
    assert dialog.result() == QDialog.DialogCode.Accepted
    assert dialog.saved_asset is not None
    stored = scopes.get_asset(project.project_id, dialog.saved_asset.asset_id)
    assert stored.asset_value == "dialog.example.test"
    assert stored.allowed_operations == ("config_check",)
