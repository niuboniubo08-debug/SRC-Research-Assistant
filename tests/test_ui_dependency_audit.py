from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml

from app.bootstrap import build_context
from core.models import Confidence, Finding, ScanTaskStatus, Severity
from scanners.base import BaseScanner, ScannerAvailability, ScanOptions, ScanOutput
from services.dependency_audit_service import DependencyAuditService
from ui.app_state import AppState
from ui.main_window import MainWindow
from ui.theme import apply_theme


class UiFakeScanner(BaseScanner):
    name = "pip-audit"
    display_name = "pip-audit"

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        return ScannerAvailability(True, "2.10.1", command="pip-audit")

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        finding = Finding(
            title="requests 2.19.0 · PYSEC-UI-1",
            category="依赖漏洞",
            severity=Severity.HIGH,
            confidence=Confidence.HIGH,
            description="UI 依赖漏洞测试说明",
            file_path=str(target),
            line_number=0,
            rule_id="PYSEC-UI-1",
            recommendation="升级 requests 至 9.9.9。",
            scanner_name="pip-audit",
            scanner_version="2.10.1",
            detected_at=datetime(2030, 1, 1, 12, tzinfo=timezone.utc),
            metadata={
                "dependency_name": "requests",
                "current_version": "2.19.0",
                "vulnerability_id": "PYSEC-UI-1",
                "aliases": ["CVE-UI-1"],
                "affected_versions": "2.19.0",
                "fix_versions": ["9.9.9"],
                "source": "pip-audit/PyPI",
            },
        )
        return ScanOutput(
            findings=(finding,),
            metadata={"audited_dependencies": 2},
        )


def _context(tmp_path: Path):
    config = {
        "app": {"name": "SRC Research Assistant", "version": "0.4.0", "environment": "test"},
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
    return build_context(
        path,
        clock=lambda: datetime(2030, 1, 1, 12, tzinfo=timezone.utc),
        expire_overdue=False,
    )


def test_dependency_page_runs_fake_pip_audit_and_displays_result(
    qtbot, tmp_path: Path
) -> None:
    from PySide6.QtWidgets import QApplication

    apply_theme(QApplication.instance())
    source = tmp_path / "project"
    source.mkdir()
    (source / "requirements.txt").write_text(
        "# test\nrequests==2.19.0\n", encoding="utf-8"
    )
    context = _context(tmp_path)
    project = context.project_service.create_project(
        "UI 依赖审计", "local_audit", "UI 集成测试", str(source), "active"
    )
    context.scope_service.create_asset(
        project.project_id,
        asset_type="local_project",
        asset_value=str(source),
    )
    fake_service = DependencyAuditService(
        context.database,
        context.audit,
        context.scope_validator,
        context.project_service,
        UiFakeScanner(),
        work_dir=context.config.storage_root / "tmp" / "ui-pip-audit",
        clock=context.clock,
    )
    context.dependency_service = fake_service
    state = AppState(context.project_service)
    state.set_active_project(project.project_id)
    window = MainWindow(context, state)
    qtbot.addWidget(window)
    window.show()
    window.navigate("dependencies")
    page = window.dependency_page
    page.refresh_all()
    qtbot.waitUntil(lambda: page.start_button.isEnabled(), timeout=15000)

    assert "requirements.txt" in page.dependency_files_label.text()
    assert "pip-audit" in page.scanner_label.text()
    page.start_button.click()
    qtbot.waitUntil(
        lambda: (
            page._task is not None  # noqa: SLF001
            and page._task.status in {ScanTaskStatus.COMPLETED, ScanTaskStatus.FAILED}
            and not page._busy  # noqa: SLF001
        ),
        timeout=20000,
    )
    assert page._task is not None  # noqa: SLF001
    assert page._task.status is ScanTaskStatus.COMPLETED  # noqa: SLF001
    assert page._task.progress == 100  # noqa: SLF001
    assert page.findings_table.rowCount() == 1
    assert page.findings_table.item(0, 1).text() == "requests"
    assert page.findings_table.item(0, 2).text() == "2.19.0"
    assert page.findings_table.item(0, 3).text() == "PYSEC-UI-1"
    page.findings_table.selectRow(0)
    qtbot.wait(50)
    assert "requests" in page.detail_title.text()
    assert "CVE-UI-1" in page.detail_meta.text()
    assert "PYSEC-UI-1" in page.detail_meta.text()
    window.close()
