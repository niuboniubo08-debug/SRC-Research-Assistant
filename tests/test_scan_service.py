from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.errors import NotFoundError, ValidationError
from core.models import Confidence, Finding, ScanTaskStatus, Severity
from scanners.base import (
    BaseScanner,
    ScanCancelled,
    ScannerAvailability,
    ScannerExecutionError,
    ScannerTimeoutError,
    ScanOptions,
    ScanOutput,
)
from services.scan_service import ScanService


def make_finding(rule_id: str = "TEST-001", severity: Severity = Severity.HIGH) -> Finding:
    return Finding(
        title=f"测试问题 {rule_id}",
        category="测试分类",
        severity=severity,
        confidence=Confidence.HIGH,
        description="测试说明",
        file_path="unsafe.py",
        line_number=3,
        rule_id=rule_id,
        recommendation="修复建议",
        scanner_name="fake",
        scanner_version="1.0",
        detected_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
    )


class FakeScanner(BaseScanner):
    name = "fake"
    display_name = "Fake"

    def __init__(
        self,
        *,
        findings: tuple[Finding, ...] = (),
        error: Exception | None = None,
        available: bool = True,
        reason: str = "",
        cancel_on_scan: bool = False,
        name: str = "fake",
        display_name: str = "Fake",
    ) -> None:
        super().__init__()
        self.name = name
        self.display_name = display_name
        self._findings = findings
        self._error = error
        self._available = available
        self._reason = reason
        self._cancel_on_scan = cancel_on_scan

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        if self._available:
            return ScannerAvailability(True, "1.0", command="fake")
        return ScannerAvailability.unavailable(self._reason or "不可用")

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        if self._cancel_on_scan:
            options.cancel_event.set()
            raise ScanCancelled("user cancelled")
        if self._error is not None:
            raise self._error
        return ScanOutput(findings=self._findings)


@pytest.fixture
def scan_context(db, audit, scope_validator, projects, local_project, local_source):
    # The fixture already contains a local project and path; create the explicit
    # local scope asset through the real service.
    from services.scope_asset_service import ScopeAssetService

    # A separate service instance is not needed for the scan, but using the
    # existing authorization service keeps fixture wiring consistent.
    return db, audit, scope_validator, projects, local_project, local_source


def make_service(db, audit, scope_validator, projects, clock, *scanners) -> ScanService:
    return ScanService(
        db, audit, scope_validator, projects, list(scanners), clock=clock
    )


def ensure_local_asset(scopes, local_project, local_source):
    scopes.create_asset(
        local_project.project_id,
        asset_type="local_project",
        asset_value=str(local_source),
    )


def test_completed_scan_persists_findings_and_task(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    scanner = FakeScanner(findings=(make_finding("FAKE-1"),))
    service = make_service(db, audit, scope_validator, projects, clock, scanner)
    progress = []
    outcome = service.run_scan(
        local_project.project_id,
        ["fake"],
        progress_callback=lambda percent, message, name: progress.append((percent, message, name)),
    )
    assert outcome.success is True
    assert outcome.task.status is ScanTaskStatus.COMPLETED
    assert outcome.task.progress == 100
    assert outcome.task.started_at is not None
    assert outcome.task.finished_at is not None
    assert len(outcome.findings) == 1
    assert outcome.findings[0].project_id == local_project.project_id
    assert outcome.findings[0].task_id == outcome.task.task_id
    assert progress
    assert progress[-1][0] >= 80
    tasks = service.list_tasks(local_project.project_id)
    assert len(tasks) == 1
    assert tasks[0].status is ScanTaskStatus.COMPLETED
    assert service.count_findings(local_project.project_id) == 1


def test_empty_scan_result_is_completed(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=())
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert outcome.success is True
    assert outcome.failed is False
    assert outcome.findings == ()
    assert "未发现匹配的安全问题" in outcome.task.result_summary


def test_scanner_execution_failure_marks_task_failed(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        clock,
        FakeScanner(error=ScannerExecutionError("tool crashed")),
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert outcome.failed is True
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "tool crashed" in outcome.task.error_message


def test_scanner_timeout_marks_task_failed(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        clock,
        FakeScanner(error=ScannerTimeoutError("timed out")),
    )
    outcome = service.run_scan(local_project.project_id, ["fake"], timeout_seconds=1)
    assert outcome.failed is True
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "超时" in outcome.task.error_message


def test_cancellation_is_not_completed(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        clock,
        FakeScanner(cancel_on_scan=True),
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert outcome.cancelled is True
    assert outcome.success is False
    assert outcome.task.status is ScanTaskStatus.CANCELLED
    assert outcome.task.cancel_requested is True
    assert outcome.task.cancelled_at is not None


def test_cancel_before_scan_marks_cancelled(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    import threading

    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=(make_finding(),))
    )
    cancel = threading.Event()
    cancel.set()
    outcome = service.run_scan(local_project.project_id, ["fake"], cancel_event=cancel)
    assert outcome.task.status is ScanTaskStatus.CANCELLED
    assert outcome.findings == ()


def test_all_unavailable_scanners_fail_without_fake_results(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        clock,
        FakeScanner(available=False, reason="missing"),
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert outcome.failed is True
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.findings == ()
    assert "均不可用" in outcome.task.error_message


def test_mixed_available_and_unavailable_reports_warning(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    available = FakeScanner(
        findings=(make_finding(),), name="fake-ok", display_name="Fake OK"
    )
    unavailable = FakeScanner(
        available=False,
        reason="tool missing",
        name="fake-missing",
        display_name="Fake Missing",
    )
    service = make_service(
        db, audit, scope_validator, projects, clock, available, unavailable
    )
    outcome = service.run_scan(
        local_project.project_id, ["fake-ok", "fake-missing"]
    )
    assert outcome.success is True
    assert outcome.scanners_run == ("fake-ok",)
    assert outcome.scanners_skipped == ("fake-missing",)
    assert any("Fake Missing" in warning for warning in outcome.warnings)
    assert len(outcome.findings) == 1


def test_project_isolation_for_tasks_and_findings(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    other = projects.create_project(
        "另一个本地项目", "local_audit", "隔离", str(local_source)
    )
    scopes.create_asset(
        other.project_id, asset_type="local_project", asset_value=str(local_source)
    )
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=(make_finding(),))
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert service.list_tasks(other.project_id) == []
    assert service.list_findings(other.project_id) == []
    with pytest.raises(NotFoundError):
        service.get_task(other.project_id, outcome.task.task_id)
    assert service.list_tasks(local_project.project_id)[0].task_id == outcome.task.task_id


def test_invalid_or_missing_path_creates_no_task(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=(make_finding(),))
    )
    shutil.rmtree(local_source)
    with pytest.raises(ValidationError):
        service.run_scan(local_project.project_id, ["fake"])
    assert service.list_tasks(local_project.project_id) == []


def test_unregistered_local_path_is_rejected(
    db, audit, scope_validator, projects, local_project, local_source, clock
) -> None:
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=(make_finding(),))
    )
    with pytest.raises(ValidationError):
        service.run_scan(local_project.project_id, ["fake"])
    assert service.list_tasks(local_project.project_id) == []


def test_finding_filters_are_scoped_and_applied(
    db, audit, scope_validator, projects, scopes, local_project, local_source, clock
) -> None:
    ensure_local_asset(scopes, local_project, local_source)
    finding = make_finding("FAKE-1", Severity.HIGH)
    service = make_service(
        db, audit, scope_validator, projects, clock, FakeScanner(findings=(finding,))
    )
    outcome = service.run_scan(local_project.project_id, ["fake"])
    assert len(service.list_findings(local_project.project_id, severity="high")) == 1
    assert service.list_findings(local_project.project_id, severity="low") == []
    assert service.list_findings(local_project.project_id, scanner_name="fake") == [
        outcome.findings[0]
    ]
    assert service.list_findings(local_project.project_id, scanner_name="other") == []


def test_scanner_infos_expose_availability(
    db, audit, scope_validator, projects, clock
) -> None:
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        clock,
        FakeScanner(available=True, name="one", display_name="One"),
        FakeScanner(available=False, reason="missing", name="two", display_name="Two"),
    )
    infos = service.scanner_infos()
    assert infos[0].available is True
    assert infos[1].available is False
    assert infos[1].reason == "missing"
