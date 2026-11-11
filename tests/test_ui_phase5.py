from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.models import FindingStatus
from tests.phase5_helpers import (
    create_project,
    insert_finding,
    make_context,
    three_scanner_findings,
)
from ui.app_state import AppState
from ui.main_window import MainWindow
from ui.theme import apply_theme


def _prepare(tmp_path: Path):
    apply_theme(QApplication.instance())
    context = make_context(tmp_path)
    project = create_project(
        context,
        tmp_path,
        name="第五阶段 UI 项目",
        directory_name="ui-project",
    )
    ids = three_scanner_findings(context.database, project.project_id)
    context.project_service.set_active_project(project.project_id)
    state = AppState(context.project_service)
    state.set_active_project(project.project_id)
    return context, state, project, ids


def test_vulnerability_page_loads_filters_and_saves_status(
    qtbot, tmp_path: Path
) -> None:
    context, state, project, ids = _prepare(tmp_path)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("vulnerabilities")
    page = window.vulnerability_page
    qtbot.waitUntil(lambda: page.table.rowCount() == 3, timeout=15000)
    assert {page.table.item(row, 4).text() for row in range(3)} == {
        "Bandit",
        "Semgrep",
        "pip-audit",
    }
    assert "第五阶段 UI 项目" in page.table.item(0, 5).text()

    page.search_edit.setText("requests")
    qtbot.waitUntil(lambda: page.table.rowCount() == 1, timeout=15000)
    assert page.table.item(0, 4).text() == "pip-audit"
    page.search_edit.clear()
    page.scanner_filter.setCurrentIndex(page.scanner_filter.findData("semgrep"))
    qtbot.waitUntil(
        lambda: (
            page.table.rowCount() == 1
            and page.table.item(0, 4).text() == "Semgrep"
        ),
        timeout=15000,
    )
    assert page.table.item(0, 4).text() == "Semgrep"
    page.scanner_filter.setCurrentIndex(0)
    qtbot.waitUntil(lambda: page.table.rowCount() == 3, timeout=15000)
    page.severity_filter.setCurrentIndex(
        page.severity_filter.findData("high")
    )
    qtbot.waitUntil(
        lambda: (
            page.table.rowCount() == 1
            and page.table.item(0, 4).text() == "Bandit"
        ),
        timeout=15000,
    )
    page.severity_filter.setCurrentIndex(0)
    qtbot.waitUntil(lambda: page.table.rowCount() == 3, timeout=15000)

    page.table.selectRow(0)
    qtbot.waitUntil(lambda: page._detail is not None, timeout=10000)  # noqa: SLF001
    page.status_combo.setCurrentIndex(
        page.status_combo.findData(FindingStatus.REVIEWING.value)
    )
    page.status_note.setText("开始复核")
    page._save_status()  # noqa: SLF001
    qtbot.waitUntil(
        lambda: (
            page._detail is not None  # noqa: SLF001
            and page._detail.finding.status == "reviewing"  # noqa: SLF001
        ),
        timeout=15000,
    )
    assert page.history_list.count() == 1
    assert "开始复核" in page.history_list.item(0).text()
    page.status_filter.setCurrentIndex(
        page.status_filter.findData(FindingStatus.REVIEWING.value)
    )
    qtbot.waitUntil(
        lambda: (
            page.table.rowCount() == 1
            and page.table.item(0, 7).text() == "审核中"
        ),
        timeout=15000,
    )
    page.status_filter.setCurrentIndex(0)
    qtbot.waitUntil(lambda: page.table.rowCount() == 3, timeout=15000)
    page.table.selectRow(0)
    qtbot.waitUntil(lambda: page._detail is not None, timeout=10000)  # noqa: SLF001

    page.notes_edit.setPlainText("人工备注 UI 测试")
    page._save_notes()  # noqa: SLF001
    qtbot.waitUntil(
        lambda: (
            page._detail is not None  # noqa: SLF001
            and page._detail.finding.manual_notes == "人工备注 UI 测试"  # noqa: SLF001
        ),
        timeout=10000,
    )

    context.evidence_service.add_evidence(
        project.project_id,
        ids["pip_audit"],
        "manual_note",
        "UI 证据",
        "已脱敏说明",
    )
    page._reload_detail(project.project_id, ids["pip_audit"])  # noqa: SLF001
    assert page.evidence_list.count() == 1
    window.close()


def test_evidence_page_selects_jumps_and_deletes_without_finding_loss(
    qtbot, tmp_path: Path
) -> None:
    context, state, project, ids = _prepare(tmp_path)
    context.evidence_service.add_evidence(
        project.project_id,
        ids["bandit"],
        "manual_note",
        "证据中心条目",
        "已脱敏证据内容",
    )
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("evidence")
    page = window.evidence_page
    qtbot.waitUntil(lambda: page.table.rowCount() == 1, timeout=15000)
    assert page.table.item(0, 0).text() == "证据中心条目"
    page.table.selectRow(0)
    qtbot.waitUntil(lambda: "证据中心条目" in page.detail_title.text(), timeout=10000)
    page._open_finding()  # noqa: SLF001
    qtbot.waitUntil(
        lambda: window.stack.currentWidget() is window.vulnerability_page,
        timeout=10000,
    )
    qtbot.waitUntil(
        lambda: (
            window.vulnerability_page._detail is not None  # noqa: SLF001
            and window.vulnerability_page._detail.finding.finding_id  # noqa: SLF001
            == ids["bandit"]
        ),
        timeout=10000,
    )
    window.navigate("evidence")
    qtbot.waitUntil(lambda: page.table.rowCount() == 1, timeout=15000)
    page.table.selectRow(0)

    import ui.evidence_page as evidence_page_module

    original_confirm = evidence_page_module.confirm
    evidence_page_module.confirm = lambda *args, **kwargs: True
    try:
        page._delete_evidence()  # noqa: SLF001
        qtbot.waitUntil(lambda: page.table.rowCount() == 0, timeout=15000)
    finally:
        evidence_page_module.confirm = original_confirm
    detail = context.vulnerability_service.get_detail(project.project_id, ids["bandit"])
    assert detail.finding.finding_id == ids["bandit"]
    assert detail.evidence == ()
    assert context.database.fetch_one(
        "SELECT COUNT(*) AS c FROM evidence WHERE project_id = ?",
        (project.project_id,),
    )["c"] == 0
    window.close()


def test_evidence_dialog_requires_finding_and_has_sensitive_confirmation(
    qtbot, tmp_path: Path
) -> None:
    context, state, project, ids = _prepare(tmp_path)
    finding = context.vulnerability_service.get_detail(
        project.project_id, ids["pip_audit"]
    ).finding
    from ui.evidence_dialog import EvidenceDialog

    dialog = EvidenceDialog(context, finding=finding)
    qtbot.addWidget(dialog)
    assert dialog.finding_combo.currentData() == ids["pip_audit"]
    assert dialog.confirm_check.isChecked() is False
    assert dialog.save_button.isEnabled() is False
    dialog.title_edit.setText("脱敏后证据")
    dialog.confirm_check.setChecked(True)
    assert dialog.save_button.isEnabled() is True
    dialog.close()
