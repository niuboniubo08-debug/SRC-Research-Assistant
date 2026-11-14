from __future__ import annotations

import shutil
import threading
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
from services.dependency_audit_service import DependencyAuditService


def make_finding(
    dependency: str = "requests",
    version: str = "2.19.0",
    vuln: str = "PYSEC-2018-28",
) -> Finding:
    return Finding(
        title=f"{dependency} {version} · {vuln}",
        category="依赖漏洞",
        severity=Severity.MEDIUM,
        confidence=Confidence.HIGH,
        description="测试依赖漏洞说明",
        file_path="requirements.txt",
        line_number=0,
        rule_id=vuln,
        recommendation="升级依赖",
        scanner_name="pip-audit",
        scanner_version="2.10.1",
        detected_at=datetime(2030, 1, 1, 12, 0, tzinfo=timezone.utc),
        metadata={
            "dependency_name": dependency,
            "current_version": version,
            "vulnerability_id": vuln,
            "aliases": ["CVE-TEST-1"],
            "affected_versions": version,
            "fix_versions": ["9.9.9"],
            "source": "pip-audit/PyPI",
            "dependency_file": "requirements.txt",
        },
    )


class FakePipAuditScanner(BaseScanner):
    name = "pip-audit"
    display_name = "pip-audit"

    def __init__(
        self,
        *,
        findings: tuple[Finding, ...] = (),
        available: bool = True,
        reason: str = "",
        error: Exception | None = None,
        cancel_on_scan: bool = False,
        audited: int = 3,
        skipped: int = 0,
        total: int | None = None,
        raw_metadata: dict[str, object] | None = None,
        warnings: tuple[str, ...] = (),
    ) -> None:
        super().__init__()
        self._findings = findings
        self._available = available
        self._reason = reason
        self._error = error
        self._cancel_on_scan = cancel_on_scan
        self._audited = audited
        self._skipped = skipped
        self._total = audited + skipped if total is None else total
        self._raw_metadata = raw_metadata
        self._warnings = warnings
        self.captured_target: Path | None = None
        self.captured_content = ""

    def is_available(self, refresh: bool = False) -> ScannerAvailability:
        if self._available:
            return ScannerAvailability(True, "2.10.1", command="pip-audit")
        return ScannerAvailability.unavailable(self._reason or "unavailable")

    def scan(self, target: str | Path, options: ScanOptions) -> ScanOutput:
        self.captured_target = Path(target)
        if Path(target).is_file():
            self.captured_content = Path(target).read_text(encoding="utf-8")
        if self._cancel_on_scan:
            options.cancel_event.set()
            raise ScanCancelled("user cancelled")
        if self._error is not None:
            raise self._error
        metadata = (
            dict(self._raw_metadata)
            if self._raw_metadata is not None
            else {
                "audited_dependencies": self._audited,
                "skipped_dependencies": self._skipped,
                "total_dependencies": self._total,
            }
        )
        return ScanOutput(
            findings=self._findings,
            warnings=self._warnings,
            metadata=metadata,
        )


def make_service(db, audit, scope_validator, projects, scanner, tmp_path):
    return DependencyAuditService(
        db,
        audit,
        scope_validator,
        projects,
        scanner,
        work_dir=tmp_path / "pip-audit-work",
    )


def ensure_asset(scopes, project, source: Path):
    scopes.create_asset(
        project.project_id,
        asset_type="local_project",
        asset_value=str(source),
    )


def test_requirements_discovery(projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "# test\nrequests==2.19.0\nurllib3==1.25.0\n", encoding="utf-8"
    )
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    discovery = service.discover(local_project.project_id)
    assert discovery.primary is not None
    assert discovery.primary.kind == "requirements"
    assert discovery.primary.dependency_count == 2
    assert discovery.primary.relative_path == "requirements.txt"


def test_pyproject_discovery(projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "pyproject.toml").write_text(
        "[project]\nname='test'\nversion='1.0'\ndependencies=['requests==2.19.0']\n",
        encoding="utf-8",
    )
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    discovery = service.discover(local_project.project_id)
    assert discovery.primary is not None
    assert discovery.primary.kind == "pyproject"
    assert discovery.primary.dependency_count == 1


def test_both_dependency_files_prefer_requirements(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    (local_source / "pyproject.toml").write_text(
        "[project]\nname='test'\nversion='1.0'\ndependencies=['urllib3==1.25.0']\n",
        encoding="utf-8",
    )
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    discovery = service.discover(local_project.project_id)
    assert discovery.primary is not None
    assert discovery.primary.kind == "requirements"


def test_no_dependency_file(projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator):
    ensure_asset(scopes, local_project, local_source)
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    discovery = service.discover(local_project.project_id)
    assert discovery.primary is None
    assert "未发现可审计依赖" in discovery.message
    with pytest.raises(ValidationError):
        service.run_audit(local_project.project_id)
    assert service.list_findings(local_project.project_id) == []


def test_completed_dependency_audit_persists_finding_and_metadata(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "# dependency\nrequests==2.19.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(make_finding(),), audited=3, skipped=0, total=3
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    progress = []
    outcome = service.run_audit(
        local_project.project_id,
        progress_callback=lambda p, m, s: progress.append((p, m, s)),
    )
    assert outcome.success is True
    assert outcome.task.status is ScanTaskStatus.COMPLETED
    assert outcome.task.progress == 100
    assert outcome.task.finished_at is not None
    assert outcome.audited_dependencies == 3
    assert outcome.dependency_file == "requirements.txt"
    assert len(outcome.findings) == 1
    finding = outcome.findings[0]
    assert finding.file_path == "requirements.txt"
    assert finding.line_number == 2
    assert finding.metadata["dependency_name"] == "requests"
    assert finding.metadata["dependency_file"] == "requirements.txt"
    assert finding.project_id == local_project.project_id
    assert finding.task_id == outcome.task.task_id
    assert progress and progress[-1][0] == 30
    stored = service.list_findings(local_project.project_id, task_id=outcome.task.task_id)
    assert len(stored) == 1
    assert stored[0].metadata["source"] == "pip-audit/PyPI"


def test_empty_dependency_result_is_completed(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("safe-package==1.0\n", encoding="utf-8")
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(), audited=1, skipped=0, total=1),
        tmp_path,
    )
    outcome = service.run_audit(local_project.project_id)
    assert outcome.success is True
    assert outcome.findings == ()
    assert "未发现已知漏洞" in outcome.task.result_summary


def test_zero_audited_dependencies_is_failure_not_success(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("safe-package==1.0\n", encoding="utf-8")
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(), audited=0),
        tmp_path,
    )
    outcome = service.run_audit(local_project.project_id)
    assert outcome.failed is True
    assert outcome.success is False
    assert "依赖审计统计非法" in outcome.task.error_message
    assert "total_dependencies 必须大于 0" in outcome.task.error_message


def test_partial_skipped_dependency_audit_fails_without_success_summary(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\nsafe-package==1.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(make_finding(),),
        audited=1,
        skipped=1,
        total=2,
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.success is False
    assert outcome.failed is True
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")


def test_all_skipped_dependency_audit_fails_without_success(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "first-skipped==1.0\nsecond-skipped==2.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(),
        audited=0,
        skipped=2,
        total=2,
        warnings=("first-skipped 未完成审计：failed to resolve",),
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.success is False
    assert outcome.failed is True
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")


def test_missing_dependency_statistics_fail_closed(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "safe-package==1.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(),
        raw_metadata={"audited_dependencies": 2},
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.success is False
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")


def test_inconsistent_dependency_statistics_fail_closed(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "safe-package==1.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(),
        raw_metadata={
            "audited_dependencies": 1,
            "skipped_dependencies": 1,
            "total_dependencies": 3,
        },
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.success is False
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")


@pytest.mark.parametrize(
    "raw_metadata",
    [
        pytest.param(
            {
                "audited_dependencies": None,
                "skipped_dependencies": 0,
                "total_dependencies": 1,
            },
            id="audited-none",
        ),
        pytest.param(
            {
                "audited_dependencies": "2",
                "skipped_dependencies": 0,
                "total_dependencies": 2,
            },
            id="audited-string",
        ),
        pytest.param(
            {
                "audited_dependencies": -1,
                "skipped_dependencies": 2,
                "total_dependencies": 1,
            },
            id="audited-negative",
        ),
        pytest.param(
            {
                "audited_dependencies": 1,
                "skipped_dependencies": 0,
                "total_dependencies": 0,
            },
            id="total-zero",
        ),
        pytest.param(
            {
                "audited_dependencies": 2,
                "skipped_dependencies": -1,
                "total_dependencies": 2,
            },
            id="skipped-negative",
        ),
        pytest.param(
            {
                "audited_dependencies": True,
                "skipped_dependencies": 0,
                "total_dependencies": 1,
            },
            id="audited-bool",
        ),
        pytest.param(
            {
                "audited_dependencies": 1,
                "skipped_dependencies": True,
                "total_dependencies": 2,
            },
            id="skipped-bool",
        ),
        pytest.param(
            {
                "audited_dependencies": 1,
                "skipped_dependencies": 0,
                "total_dependencies": True,
            },
            id="total-bool",
        ),
    ],
)
def test_invalid_dependency_statistics_fail_closed(
    projects,
    scopes,
    local_project,
    local_source,
    tmp_path,
    db,
    audit,
    scope_validator,
    raw_metadata,
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "safe-package==1.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(findings=(), raw_metadata=raw_metadata)
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert outcome.success is False
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")


def test_pip_audit_unavailable_marks_task_failed_without_findings(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(available=False, reason="missing"),
        tmp_path,
    )
    outcome = service.run_audit(local_project.project_id)
    assert outcome.failed is True
    assert outcome.findings == ()
    assert "missing" in outcome.task.error_message
    assert service.latest_task(local_project.project_id).status is ScanTaskStatus.FAILED


def test_execution_failure_and_timeout_are_failed(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    for error in (
        ScannerExecutionError("execution failed"),
        ScannerTimeoutError("timed out"),
    ):
        scanner = FakePipAuditScanner(error=error)
        service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
        outcome = service.run_audit(local_project.project_id, timeout_seconds=1)
        assert outcome.failed is True
        assert outcome.task.status is ScanTaskStatus.FAILED
        assert str(error) in outcome.task.error_message


def test_cancelled_dependency_audit_is_not_completed(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    scanner = FakePipAuditScanner(cancel_on_scan=True)
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.cancelled is True
    assert outcome.task.status is ScanTaskStatus.CANCELLED
    assert outcome.task.cancel_requested is True
    assert outcome.task.cancelled_at is not None
    assert outcome.task.status is not ScanTaskStatus.COMPLETED


def test_cancel_before_start_marks_cancelled(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    cancel = threading.Event()
    cancel.set()
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    outcome = service.run_audit(local_project.project_id, cancel_event=cancel)
    assert outcome.cancelled is True
    assert outcome.findings == ()


def test_pyproject_is_prepared_as_temporary_requirements_and_cleaned(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "pyproject.toml").write_text(
        "[project]\nname='test'\nversion='1.0'\n"
        "dependencies=['requests==2.19.0', 'urllib3==1.25.0']\n",
        encoding="utf-8",
    )
    scanner = FakePipAuditScanner(findings=(make_finding(),), audited=2)
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    outcome = service.run_audit(local_project.project_id)
    assert outcome.success is True
    assert scanner.captured_target is not None
    assert scanner.captured_target.name == "requirements.txt"
    assert "requests==2.19.0" in scanner.captured_content
    assert "urllib3==1.25.0" in scanner.captured_content
    assert not any((tmp_path / "pip-audit-work").glob("pyproject-*"))


def test_dependency_project_isolation(
    db, audit, scope_validator, projects, scopes, local_project, local_source, tmp_path
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    other_dir = tmp_path / "other-project"
    other_dir.mkdir()
    (other_dir / "requirements.txt").write_text("urllib3==1.25.0\n", encoding="utf-8")
    other = projects.create_project("其他依赖项目", "local_audit", "隔离", str(other_dir))
    scopes.create_asset(
        other.project_id, asset_type="local_project", asset_value=str(other_dir)
    )
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(make_finding(),)),
        tmp_path,
    )
    outcome = service.run_audit(local_project.project_id)
    assert service.list_findings(other.project_id) == []
    assert service.latest_task(other.project_id) is None
    with pytest.raises(NotFoundError):
        service.get_task(other.project_id, outcome.task.task_id)


def test_unregistered_path_is_rejected(
    projects, local_project, local_source, tmp_path, db, audit, scope_validator
):
    (local_source / "requirements.txt").write_text("requests==2.19.0\n", encoding="utf-8")
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    with pytest.raises(ValidationError):
        service.discover(local_project.project_id)
    with pytest.raises(ValidationError):
        service.run_audit(local_project.project_id)


def test_invalid_pyproject_is_not_auditable(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "pyproject.toml").write_text("not = [valid", encoding="utf-8")
    service = make_service(db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path)
    discovery = service.discover(local_project.project_id)
    assert discovery.primary is None
    assert discovery.files
    assert discovery.files[0].supported is False


@pytest.fixture
def statistics_service(db, audit, scope_validator, projects, tmp_path):
    return make_service(
        db, audit, scope_validator, projects, FakePipAuditScanner(), tmp_path
    )


@pytest.mark.parametrize(
    "metadata",
    [None, []],
    ids=["none", "list"],
)
def test_validate_statistics_rejects_non_mapping(statistics_service, metadata):
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(metadata)


@pytest.mark.parametrize(
    "field",
    ["audited_dependencies", "skipped_dependencies", "total_dependencies"],
)
def test_validate_statistics_rejects_missing_field(statistics_service, field):
    metadata = {
        "audited_dependencies": 2,
        "skipped_dependencies": 0,
        "total_dependencies": 2,
    }
    del metadata[field]
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(metadata)


@pytest.mark.parametrize(
    "field",
    ["audited_dependencies", "skipped_dependencies", "total_dependencies"],
)
@pytest.mark.parametrize(
    "value",
    [None, True, False, "2", 2.0],
    ids=["none", "true", "false", "str", "float"],
)
def test_validate_statistics_rejects_non_int_types(statistics_service, field, value):
    metadata = {
        "audited_dependencies": 2,
        "skipped_dependencies": 0,
        "total_dependencies": 2,
    }
    metadata[field] = value
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(metadata)


@pytest.mark.parametrize(
    "field",
    ["audited_dependencies", "skipped_dependencies", "total_dependencies"],
)
def test_validate_statistics_rejects_negative_fields(statistics_service, field):
    metadata = {
        "audited_dependencies": 2,
        "skipped_dependencies": 0,
        "total_dependencies": 2,
    }
    metadata[field] = -1
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(metadata)


def test_validate_statistics_rejects_zero_total(statistics_service):
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(
            {
                "audited_dependencies": 0,
                "skipped_dependencies": 0,
                "total_dependencies": 0,
            }
        )


def test_validate_statistics_rejects_sum_mismatch(statistics_service):
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(
            {
                "audited_dependencies": 2,
                "skipped_dependencies": 1,
                "total_dependencies": 4,
            }
        )


def test_validate_statistics_rejects_inconsistent_incomplete_total(statistics_service):
    with pytest.raises(ValidationError):
        statistics_service._validate_statistics(
            {
                "audited_dependencies": 1,
                "skipped_dependencies": 0,
                "total_dependencies": 2,
            }
        )


def test_validate_statistics_returns_complete_tuple(statistics_service):
    assert statistics_service._validate_statistics(
        {
            "audited_dependencies": 2,
            "skipped_dependencies": 0,
            "total_dependencies": 2,
        }
    ) == (2, 0, 2)


def test_validate_statistics_returns_incomplete_tuple(statistics_service):
    assert statistics_service._validate_statistics(
        {
            "audited_dependencies": 1,
            "skipped_dependencies": 1,
            "total_dependencies": 2,
        }
    ) == (1, 1, 2)


def test_invalid_statistics_skip_finding_mapping_and_saving(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator, monkeypatch
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(make_finding(),),
        raw_metadata={"audited_dependencies": 1, "skipped_dependencies": 0},
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    calls = []
    original_map = service._map_findings
    original_save = service._save_findings

    def map_spy(discovery, selected, findings):
        calls.append("map")
        return original_map(discovery, selected, findings)

    def save_spy(project_id, task_id, findings):
        calls.append("save")
        return original_save(project_id, task_id, findings)

    monkeypatch.setattr(service, "_map_findings", map_spy)
    monkeypatch.setattr(service, "_save_findings", save_spy)
    outcome = service.run_audit(local_project.project_id)

    assert calls == []
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "依赖审计统计非法" in outcome.task.error_message
    assert outcome.findings == ()
    assert service.list_findings(local_project.project_id) == []


def test_incomplete_statistics_map_then_save_and_fail_without_success_summary(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator, monkeypatch
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\nsafe-package==1.0\n", encoding="utf-8"
    )
    scanner = FakePipAuditScanner(
        findings=(make_finding(),), audited=1, skipped=1, total=2
    )
    service = make_service(db, audit, scope_validator, projects, scanner, tmp_path)
    calls = []
    original_map = service._map_findings
    original_save = service._save_findings

    def map_spy(discovery, selected, findings):
        calls.append("map")
        return original_map(discovery, selected, findings)

    def save_spy(project_id, task_id, findings):
        calls.append("save")
        return original_save(project_id, task_id, findings)

    monkeypatch.setattr(service, "_map_findings", map_spy)
    monkeypatch.setattr(service, "_save_findings", save_spy)
    outcome = service.run_audit(local_project.project_id)

    assert calls == ["map", "save"]
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "审计不完整" in outcome.task.error_message
    assert "未发现已知漏洞" not in str(outcome.task.result_summary or "")
    assert len(outcome.findings) == 1
    stored = service.list_findings(local_project.project_id, task_id=outcome.task.task_id)
    assert len(stored) == 1


def test_statistics_validation_error_skips_mapping_and_returns_statistics_error(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator, monkeypatch
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\n", encoding="utf-8"
    )
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(make_finding(),)),
        tmp_path,
    )
    calls = []

    def raise_validation_error(metadata):
        calls.append("validate")
        raise ValidationError("测试统计损坏")

    def fail_if_mapped(*args, **kwargs):
        calls.append("map")
        raise AssertionError("统计非法时不应映射 Finding")

    def fail_if_saved(*args, **kwargs):
        calls.append("save")
        raise AssertionError("统计非法时不应保存 Finding")

    monkeypatch.setattr(service, "_validate_statistics", raise_validation_error)
    monkeypatch.setattr(service, "_map_findings", fail_if_mapped)
    monkeypatch.setattr(service, "_save_findings", fail_if_saved)
    outcome = service.run_audit(local_project.project_id)

    assert calls == ["validate"]
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "依赖审计统计非法：测试统计损坏" in outcome.task.error_message
    assert service.list_findings(local_project.project_id) == []


def test_statistics_unexpected_exception_is_labeled_and_skips_mapping(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator, monkeypatch
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\n", encoding="utf-8"
    )
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(make_finding(),)),
        tmp_path,
    )
    calls = []

    def raise_runtime_error(metadata):
        calls.append("validate")
        raise RuntimeError("boom")

    def fail_if_mapped(*args, **kwargs):
        calls.append("map")
        raise AssertionError("统计异常时不应映射 Finding")

    def fail_if_saved(*args, **kwargs):
        calls.append("save")
        raise AssertionError("统计异常时不应保存 Finding")

    monkeypatch.setattr(service, "_validate_statistics", raise_runtime_error)
    monkeypatch.setattr(service, "_map_findings", fail_if_mapped)
    monkeypatch.setattr(service, "_save_findings", fail_if_saved)
    outcome = service.run_audit(local_project.project_id)

    assert calls == ["validate"]
    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "依赖审计统计校验异常：boom" in outcome.task.error_message
    assert "依赖审计统计非法" not in outcome.task.error_message
    assert service.list_findings(local_project.project_id) == []


def test_finding_save_exception_is_not_reported_as_statistics_error(
    projects, scopes, local_project, local_source, tmp_path, db, audit, scope_validator, monkeypatch
):
    ensure_asset(scopes, local_project, local_source)
    (local_source / "requirements.txt").write_text(
        "requests==2.19.0\n", encoding="utf-8"
    )
    service = make_service(
        db,
        audit,
        scope_validator,
        projects,
        FakePipAuditScanner(findings=(), audited=1, skipped=0, total=1),
        tmp_path,
    )

    def fail_to_save(project_id, task_id, findings):
        raise OSError("disk full")

    monkeypatch.setattr(service, "_save_findings", fail_to_save)
    outcome = service.run_audit(local_project.project_id)

    assert outcome.task.status is ScanTaskStatus.FAILED
    assert "依赖审计结果保存失败：disk full" in outcome.task.error_message
    assert "依赖审计统计非法" not in outcome.task.error_message
    assert "依赖审计统计校验异常" not in outcome.task.error_message
    assert service.list_findings(local_project.project_id) == []
