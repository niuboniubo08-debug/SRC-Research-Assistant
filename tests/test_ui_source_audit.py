from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.bootstrap import build_context
from core.models import ScanTaskStatus
from ui.app_state import AppState
from ui.main_window import MainWindow
from ui.theme import apply_theme


def _context(tmp_path: Path):
    config = {
        "app": {"name": "SRC Research Assistant", "version": "0.3.0", "environment": "test"},
        "database": {"path": "storage/test.db"},
        "storage": {
            "root": "storage",
            "projects": "storage/projects",
            "evidence": "storage/evidence",
            "reports": "storage/reports",
            "logs": "storage/logs",
        },
        "ui": {"theme": "dark", "window_width": 1280, "window_height": 800},
        "security": {
            "default_remote_access": "deny",
            "require_valid_authorization": True,
            "allow_wildcard_scope": False,
            "allow_redirect_following": False,
            "require_exact_remote_match": True,
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return build_context(path, clock=lambda: datetime(2030, 1, 1, 12, tzinfo=timezone.utc), expire_overdue=False)


def test_source_audit_page_runs_real_local_bandit_scan(qtbot, tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication

    apply_theme(QApplication.instance())
    source = tmp_path / "source"
    source.mkdir()
    (source / "unsafe.py").write_text(
        "import subprocess\n"
        "def run(user):\n"
        "    eval(user)\n"
        "    subprocess.run(user, shell=True)\n",
        encoding="utf-8",
    )
    context = _context(tmp_path)
    project = context.project_service.create_project(
        "UI 本地扫描", "local_audit", "UI 集成测试", str(source), "active"
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="local_project",
        asset_value=str(source),
    )
    state = AppState(context.project_service)
    state.set_active_project(project.project_id)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("source_audit")
    page = window.source_audit_page
    page.refresh_all()
    qtbot.waitUntil(lambda: page.start_button.isEnabled(), timeout=15000)

    assert "已授权" in page.path_pill.text()
    assert page.scanner_checkboxes["bandit"].isChecked()
    # Semgrep may be available on another machine, but if unavailable it must be
    # disabled and show a reason rather than silently running.
    if page._scanner_infos["semgrep"].available:  # noqa: SLF001
        assert page.scanner_checkboxes["semgrep"].isEnabled()
    else:
        assert not page.scanner_checkboxes["semgrep"].isEnabled()
        assert page.scanner_state_labels["semgrep"].text() == "不可用"
        assert "Semgrep" in page.scanner_notes.text()

    page.start_button.click()
    qtbot.waitUntil(
        lambda: (
            page._task is not None  # noqa: SLF001
            and page._task.status in {ScanTaskStatus.COMPLETED, ScanTaskStatus.FAILED}
            and not page._busy  # noqa: SLF001
        ),
        timeout=30000,
    )
    assert page._task is not None  # noqa: SLF001
    assert page._task.status is ScanTaskStatus.COMPLETED  # noqa: SLF001
    assert page._task.progress == 100  # noqa: SLF001
    assert page.findings_table.rowCount() > 0
    assert page.scan_status.text() == "已完成"
    page.findings_table.selectRow(0)
    qtbot.wait(50)
    assert page.detail_title.text() not in {"", "暂无结果"}

    page.severity_filter.setCurrentIndex(page.severity_filter.findData("high"))
    page._refresh_findings()  # noqa: SLF001
    assert page.findings_table.rowCount() > 0
    for row in range(page.findings_table.rowCount()):
        assert page.findings_table.item(row, 0).text() == "高危"
    page.severity_filter.setCurrentIndex(0)
    page.scanner_filter.setCurrentIndex(page.scanner_filter.findData("bandit"))
    page._refresh_findings()  # noqa: SLF001
    assert page.findings_table.rowCount() > 0
    for row in range(page.findings_table.rowCount()):
        assert page.findings_table.item(row, 5).text() == "Bandit"
    window.close()
