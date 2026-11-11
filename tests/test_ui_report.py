"""Phase 6C-2B Step 2 UI tests for the report center.

The tests use local fixture data only.  Export is monkeypatched in most cases;
one assertion verifies the fixed reports directory and the default
``overwrite=False`` call.  The exporter security suite remains separate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtWidgets import QApplication

from core.models.report import ReportArtifact, ReportFormat, ReportType
from tests.phase5_helpers import create_project, insert_finding, insert_task, make_context
from ui.app_state import AppState
from ui.main_window import MainWindow
from ui.report_page import ReportPage
from ui.theme import apply_theme


def _page(tmp_path: Path, *, with_finding: bool = True):
    apply_theme(QApplication.instance())
    context = make_context(tmp_path)
    project = create_project(
        context,
        tmp_path,
        name="报告中心测试项目",
        directory_name="report-ui-project",
    )
    if with_finding:
        task_id = insert_task(context.database, project.project_id)
        insert_finding(
            context.database,
            project.project_id,
            title="报告中心测试 Finding",
            scanner_name="bandit",
            rule_id="B307",
            task_id=task_id,
        )
    context.project_service.set_active_project(project.project_id)
    state = AppState(context.project_service)
    page = ReportPage(context, state)
    return context, state, project, page


def _artifact(request, snapshot, reports_dir: str | Path) -> ReportArtifact:
    return ReportArtifact(
        report_type=request.report_type,
        report_format=ReportFormat.HTML,
        project_id=request.project_id,
        title=request.title or "测试报告",
        generated_at=snapshot.generated_at,
        snapshot_id=snapshot.snapshot_id,
        path=str(Path(reports_dir) / "project_test.html"),
        sha256="a" * 64,
        warnings=snapshot.warnings,
    )


def test_no_active_project_disables_actions_and_clears_snapshot(
    qtbot, tmp_path: Path
) -> None:
    apply_theme(QApplication.instance())
    context = make_context(tmp_path)
    state = AppState(context.project_service)
    page = ReportPage(context, state)
    qtbot.addWidget(page)

    assert state.current_project is None
    assert page._snapshot is None  # noqa: SLF001
    assert not page.preview_button.isEnabled()
    assert not page.export_button.isEnabled()
    assert "未选择活动项目" in page.project_label.text()


def test_removing_active_project_clears_snapshot_and_disables_actions(
    qtbot, tmp_path: Path
) -> None:
    _context, state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    page._ensure_snapshot()  # noqa: SLF001
    assert page._snapshot is not None  # noqa: SLF001

    state.set_active_project(None)

    assert page._snapshot is None  # noqa: SLF001
    assert not page.preview_button.isEnabled()
    assert not page.export_button.isEnabled()
    assert "未选择活动项目" in page.project_label.text()


def test_project_change_invalidates_snapshot(qtbot, tmp_path: Path) -> None:
    context, state, project, page = _page(tmp_path)
    qtbot.addWidget(page)
    first = page._ensure_snapshot()  # noqa: SLF001
    assert first.project_id == project.project_id
    assert page.preview_button.isEnabled()

    second = create_project(
        context,
        tmp_path,
        name="第二个报告项目",
        directory_name="report-ui-project-2",
    )
    state.set_active_project(second.project_id)

    assert page._snapshot is None  # noqa: SLF001
    assert "请先生成预览" in page.preview.toPlainText()
    assert page.export_button.isEnabled()


def test_report_type_change_invalidates_snapshot(qtbot, tmp_path: Path) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    page._ensure_snapshot()  # noqa: SLF001
    assert page._selected_type() is ReportType.VULNERABILITY  # noqa: SLF001

    page.report_type_combo.setCurrentIndex(1)

    assert page._snapshot is None  # noqa: SLF001
    assert "报告类型已切换" in page.status_label.text()
    assert "请先生成预览" in page.preview.toPlainText()


def test_preview_uses_render_html_and_never_calls_writer(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    calls: list[tuple] = []
    writer_calls: list[tuple] = []

    def fake_render(snapshot, request):
        calls.append((snapshot, request))
        return "<html><body><p>SAFE_PREVIEW</p></body></html>"

    def fail_writer(*args, **kwargs):
        writer_calls.append((args, kwargs))
        raise AssertionError("preview must not call write_html_report")

    monkeypatch.setattr("ui.report_page.render_html", fake_render)
    monkeypatch.setattr("ui.report_page.write_html_report", fail_writer)

    page.preview_button.click()

    assert len(calls) == 1
    assert calls[0][1].report_format is ReportFormat.HTML
    assert writer_calls == []
    assert "SAFE_PREVIEW" in page.preview.toPlainText()
    assert "尚未写入文件" in page.status_label.text()


def test_export_uses_fixed_reports_dir_and_default_overwrite(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    calls: list[tuple] = []

    def fake_write(snapshot, request, reports_dir, **kwargs):
        calls.append((snapshot, request, reports_dir, kwargs))
        return _artifact(request, snapshot, reports_dir)

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)
    page.title_edit.setText("自定义报告标题")
    page.include_notes_check.setChecked(False)

    page.export_button.click()

    assert len(calls) == 1
    _snapshot, request, reports_dir, kwargs = calls[0]
    assert reports_dir == context.config.reports_dir
    assert kwargs == {"overwrite": False, "filename": None}
    assert request.title == "自定义报告标题"
    assert request.include_notes is False
    assert "导出成功" in page.status_label.text()
    assert str(context.config.reports_dir) in page.output_label.text()


def test_export_writes_real_html_inside_fixed_reports_dir(
    qtbot, tmp_path: Path
) -> None:
    context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)

    page.export_button.click()

    reports = list(context.config.reports_dir.glob("*.html"))
    assert len(reports) == 1
    assert reports[0].parent == context.config.reports_dir
    html = reports[0].read_text(encoding="utf-8")
    assert "报告中心测试项目" in html
    assert "导出成功" in page.status_label.text()


def test_file_exists_confirm_then_retries_with_overwrite_true(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    attempts: list[bool] = []

    def fake_write(snapshot, request, reports_dir, **kwargs):
        attempts.append(kwargs["overwrite"])
        if len(attempts) == 1:
            raise FileExistsError("already exists")
        return _artifact(request, snapshot, reports_dir)

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)
    monkeypatch.setattr("ui.report_page.confirm", lambda *args, **kwargs: True)

    page.export_button.click()

    assert attempts == [False, True]
    assert "导出成功" in page.status_label.text()


def test_file_exists_decline_does_not_overwrite(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    attempts: list[bool] = []

    def fake_write(snapshot, request, reports_dir, **kwargs):
        attempts.append(kwargs["overwrite"])
        raise FileExistsError("already exists")

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)
    monkeypatch.setattr("ui.report_page.confirm", lambda *args, **kwargs: False)

    page.export_button.click()

    assert attempts == [False]
    assert "已取消" in page.status_label.text()


def test_export_exception_restores_buttons_and_does_not_show_success(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    errors: list[Exception] = []

    def fail_write(*args, **kwargs):
        raise RuntimeError("simulated export failure")

    monkeypatch.setattr("ui.report_page.write_html_report", fail_write)
    monkeypatch.setattr(
        "ui.report_page.show_error",
        lambda parent, exc, title: errors.append(exc),
    )

    page.export_button.click()

    assert len(errors) == 1
    assert page.preview_button.isEnabled()
    assert page.export_button.isEnabled()
    assert "导出失败" in page.status_label.text()
    assert "成功" not in page.output_label.text()
    assert page._exporting is False  # noqa: SLF001


def test_exporting_guard_prevents_reentry(qtbot, tmp_path: Path, monkeypatch) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    calls = 0

    def fake_write(snapshot, request, reports_dir, **kwargs):
        nonlocal calls
        calls += 1
        page.export()  # must return immediately because _exporting is true
        return _artifact(request, snapshot, reports_dir)

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)

    page.export()

    assert calls == 1
    assert page._exporting is False  # noqa: SLF001


def test_repeated_preview_fetches_a_fresh_snapshot(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    original = page._service.get_snapshot  # noqa: SLF001
    snapshots = []

    def counted(*args, **kwargs):
        snapshot = original(*args, **kwargs)
        snapshots.append(snapshot)
        return snapshot

    monkeypatch.setattr(page._service, "get_snapshot", counted)  # noqa: SLF001

    page.generate_preview()
    first_id = page._snapshot.snapshot_id  # noqa: SLF001
    page.generate_preview()
    second_id = page._snapshot.snapshot_id  # noqa: SLF001

    assert len(snapshots) == 2
    assert first_id != second_id
    assert "预览已生成" in page.status_label.text()


def test_manual_refresh_invalidates_snapshot_and_clears_preview(
    qtbot, tmp_path: Path
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    page.generate_preview()
    assert page._snapshot is not None  # noqa: SLF001
    assert "报告中心测试项目" in page.preview.toPlainText()

    page.refresh()

    assert page._snapshot is None  # noqa: SLF001
    assert "请先生成预览" in page.preview.toPlainText()
    assert "请先生成预览" in page.status_label.text()


def test_export_fetches_a_fresh_snapshot_after_preview(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    page.generate_preview()
    preview_id = page._snapshot.snapshot_id  # noqa: SLF001
    exported: list = []

    def fake_write(snapshot, request, reports_dir, **kwargs):
        exported.append(snapshot)
        return _artifact(request, snapshot, reports_dir)

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)

    page.export()

    assert len(exported) == 1
    assert exported[0].snapshot_id != preview_id
    assert "导出成功" in page.status_label.text()


def test_overwrite_retry_reuses_the_same_snapshot_and_request(
    qtbot, tmp_path: Path, monkeypatch
) -> None:
    _context, _state, _project, page = _page(tmp_path)
    qtbot.addWidget(page)
    attempts: list[bool] = []
    snapshots: list = []
    requests: list = []

    def fake_write(snapshot, request, reports_dir, **kwargs):
        attempts.append(kwargs["overwrite"])
        snapshots.append(snapshot)
        requests.append(request)
        if len(attempts) == 1:
            raise FileExistsError("already exists")
        return _artifact(request, snapshot, reports_dir)

    monkeypatch.setattr("ui.report_page.write_html_report", fake_write)
    monkeypatch.setattr("ui.report_page.confirm", lambda *args, **kwargs: True)

    page.export_button.click()

    assert attempts == [False, True]
    assert snapshots[0] is snapshots[1]
    assert requests[0] is requests[1]
    assert "导出成功" in page.status_label.text()


def test_main_window_uses_report_page_and_context_service(
    qtbot, tmp_path: Path
) -> None:
    apply_theme(QApplication.instance())
    context = make_context(tmp_path)
    project = create_project(
        context,
        tmp_path,
        name="窗口报告项目",
        directory_name="window-report-project",
    )
    context.project_service.set_active_project(project.project_id)
    state = AppState(context.project_service)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("reports")

    assert window.report_page is window.pages_by_key["reports"]
    assert isinstance(window.report_page, ReportPage)
    assert window.report_page._context.report_service is context.report_service  # noqa: SLF001
