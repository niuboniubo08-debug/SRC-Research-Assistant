from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import yaml

from app.bootstrap import build_context
from ui.app_state import AppState
from ui.main_window import MainWindow
from ui.theme import apply_theme


def _make_context(tmp_path: Path, clock):
    config = {
        "app": {"name": "SRC Research Assistant", "version": "0.2.0", "environment": "test"},
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
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    return build_context(config_path, clock=clock, expire_overdue=False)


def test_main_window_pages_and_navigation(qtbot, tmp_path, clock) -> None:
    from PySide6.QtWidgets import QApplication

    apply_theme(QApplication.instance())
    context = _make_context(tmp_path, clock)
    state = AppState(context.project_service)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()

    from PySide6.QtCore import Qt

    assert len(window.nav_buttons) == 10
    assert window.stack.count() == 10
    assert window.project_page.tabs.count() == 4
    assert window.windowFlags() & Qt.WindowType.WindowMaximizeButtonHint
    assert window.windowFlags() & Qt.WindowType.WindowCloseButtonHint
    for key in window.pages_by_key:
        window.navigate(key)
        assert window.stack.currentWidget() is window.pages_by_key[key]


def test_project_page_displays_and_filters_data(qtbot, tmp_path, clock) -> None:
    from PySide6.QtWidgets import QApplication

    apply_theme(QApplication.instance())
    context = _make_context(tmp_path, clock)
    project = context.project_service.create_project("Alpha 授权项目", "authorized_test")
    context.project_service.create_project("Beta 本地项目", "local_audit")
    auth = context.authorization_service.create_authorization(
        project.project_id,
        authorization_source="测试授权",
        authorization_document="C:/fake/authorization.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=30),
        authorization_status="confirmed",
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="domain",
        asset_value="example.com",
        authorization_id=auth.authorization_id,
        allowed_operations=["config_check"],
    )
    state = AppState(context.project_service)
    state.set_active_project(project.project_id)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("projects")
    page = window.project_page
    page.refresh_all()

    assert page.project_table.rowCount() == 2
    assert page.auth_table.rowCount() == 1
    assert page.asset_table.rowCount() == 1
    assert "Alpha" in page._context_label.text()  # noqa: SLF001 - UI assertion
    assert page.auth_table.item(0, 6).text() == "有效"

    page.search_edit.setText("Alpha")
    page.refresh_projects()
    assert page.project_table.rowCount() == 1
    page.search_edit.clear()
    page.refresh_projects()
    assert page.project_table.rowCount() == 2

    window.project_combo.setCurrentIndex(0)
    assert state.current_project is None
