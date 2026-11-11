"""Phase-6 B tests: read-only report snapshots and project isolation.

All data in this file is deterministic test fixture data.  No scanner is run
and no remote target is contacted.
"""

from __future__ import annotations

import hashlib
from dataclasses import FrozenInstanceError
from datetime import timedelta
from pathlib import Path

import pytest

from core.errors import NotFoundError, ValidationError
from core.models.enums import AuthStatus, EvidenceType, FindingStatus, Severity
from core.models.report import (
    ReportFormat,
    ReportRequest,
    ReportSnapshot,
    ReportType,
)
from repositories.report_repository import ReportRepository
from services.report_service import ReportService
from tests.phase5_helpers import insert_finding, insert_task


@pytest.fixture
def report_repo(db, clock) -> ReportRepository:
    return ReportRepository(db, clock=clock)


@pytest.fixture
def managed_root(tmp_path: Path) -> Path:
    return tmp_path / "managed-evidence"


@pytest.fixture
def report_service(db, report_repo, managed_root: Path, clock) -> ReportService:
    return ReportService(
        db, report_repo, evidence_root=managed_root, clock=clock
    )


@pytest.fixture
def seeded(db, local_project, local_asset, authorizations, clock):
    return _seed_project(db, local_project, local_asset, authorizations, clock)


def _confirmed_auth(authorizations, project, clock, *, source: str = "测试书面授权"):
    return authorizations.create_authorization(
        project.project_id,
        authorization_source=source,
        authorization_document="C:/authorized/report-scope.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=30),
        authorization_status=AuthStatus.CONFIRMED,
    )


def _add_evidence(
    db,
    project_id: int,
    finding_id: int,
    *,
    evidence_type: str = "code_snippet",
    title: str = "测试证据",
    description: str = "测试证据说明",
    file_path: str = "",
    file_name: str = "",
    file_hash: str = "",
    source: str = "fixture",
) -> int:
    with db.transaction() as conn:
        cursor = conn.execute(
            "INSERT INTO evidence "
            "(project_id, finding_id, evidence_type, title, description, "
            "file_path, file_name, sha256, captured_at, source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                project_id,
                finding_id,
                evidence_type,
                title,
                description,
                file_path,
                file_name,
                file_hash,
                "2030-01-01T12:00:00Z",
                source,
                "2030-01-01T12:00:00Z",
            ),
        )
        return int(cursor.lastrowid or 0)


def _seed_project(db, local_project, local_asset, authorizations, clock):
    _confirmed_auth(authorizations, local_project, clock)
    task_id = insert_task(
        db,
        local_project.project_id,
        task_type="source_audit",
        target="unsafe.py",
        status="completed",
    )
    finding_ids = {
        "bandit": insert_finding(
            db,
            local_project.project_id,
            title="Bandit: eval 使用",
            scanner_name="bandit",
            rule_id="B307",
            severity="high",
            category="代码执行",
            task_id=task_id,
            metadata={
                "bandit_test_id": ["B307"],
                "source": "fixture",
                "arbitrary_private_value": "not-for-report",
            },
        ),
        "semgrep": insert_finding(
            db,
            local_project.project_id,
            title="Semgrep: subprocess shell",
            scanner_name="semgrep",
            rule_id="python.subprocess-shell",
            severity="medium",
            category="命令执行",
            task_id=task_id,
            metadata={"semgrep_check_id": "python.subprocess-shell"},
        ),
        "pip": insert_finding(
            db,
            local_project.project_id,
            title="requests 2.19.0 · PYSEC-TEST-1",
            scanner_name="pip-audit",
            rule_id="PYSEC-TEST-1",
            severity="medium",
            category="依赖漏洞",
            file_path="requirements.txt",
            metadata={
                "dependency_name": "requests",
                "current_version": "2.19.0",
                "vulnerability_id": "PYSEC-TEST-1",
                "aliases": ["CVE-TEST-1"],
                "fix_versions": ["9.9.9"],
                "affected_versions": "当前审计版本 2.19.0 命中",
                "source": "pip-audit/PyPI",
                "severity_source": "conservative-default",
            },
        ),
    }
    text_id = _add_evidence(
        db,
        local_project.project_id,
        finding_ids["pip"],
        evidence_type="dependency_info",
        title="依赖漏洞摘要",
        description="测试文本证据",
    )
    return task_id, finding_ids, text_id


def test_three_report_snapshots(report_service, local_project, seeded):
    snapshots = {
        kind: report_service.get_snapshot(local_project.project_id, kind)
        for kind in ReportType
    }
    for kind, snapshot in snapshots.items():
        assert snapshot.report_type is kind
        assert snapshot.project.project_id == local_project.project_id
        assert snapshot.project.project_name == local_project.project_name
        assert snapshot.stats is not None
        assert snapshot.stats.finding_count == 3
        assert snapshot.stats.evidence_count == 1
        assert snapshot.stats.file_evidence_count == 0
        assert snapshot.generated_at == snapshot.authorization.as_of
        assert snapshot.data_scope
        assert "项目" not in snapshot.data_scope
        assert any("metadata" in text for text in snapshot.warnings)
        assert snapshot.known_limitations
        assert snapshot.schema_version == 5
    assert snapshots[ReportType.VULNERABILITY].data_scope != snapshots[
        ReportType.PROJECT_SUMMARY
    ].data_scope


def test_default_snapshot_type_is_project_summary(
    report_repo, local_project, seeded
):
    snapshot = report_repo.load_snapshot(local_project.project_id)
    assert snapshot.report_type is ReportType.PROJECT_SUMMARY
    assert snapshot.stats is None
    assert snapshot.findings


def test_stats_and_dependency_metadata(report_service, local_project, seeded):
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.PROJECT_SUMMARY
    )
    stats = snapshot.stats
    assert stats is not None
    assert stats.task_count == 1
    assert stats.task_status_counts["completed"] == 1
    assert stats.task_scanner_counts["bandit"] == 1
    assert stats.finding_count == 3
    assert stats.severity_counts["high"] == 1
    assert stats.severity_counts["medium"] == 2
    assert stats.severity_counts["critical"] == 0
    assert stats.scanner_counts["bandit"] == 1
    assert stats.scanner_counts["semgrep"] == 1
    assert stats.scanner_counts["pip-audit"] == 1
    assert stats.finding_status_counts["open"] == 3
    assert stats.dependency_finding_count == 1
    assert stats.evidence_type_counts["dependency_info"] == 1
    assert stats.evidence_type_counts["screenshot"] == 0
    assert stats.file_evidence_count == 0

    pip = next(item for item in snapshot.findings if item.scanner_name == "pip-audit")
    assert pip.dependency_name == "requests"
    assert pip.dependency_version == "2.19.0"
    assert pip.vulnerability_id == "PYSEC-TEST-1"
    assert pip.fix_versions == ("9.9.9",)
    assert pip.affected_versions == "当前审计版本 2.19.0 命中"
    assert pip.severity_source == "conservative-default"
    assert pip.metadata["source"] == "pip-audit/PyPI"
    assert pip.raw_metadata_omitted is False

    bandit = next(item for item in snapshot.findings if item.scanner_name == "bandit")
    assert bandit.raw_metadata_omitted is True
    assert "arbitrary_private_value" not in bandit.metadata
    assert bandit.vulnerability_id is None


def test_empty_project_snapshot(report_service, projects):
    project = projects.create_project("空项目", "local_audit", "没有扫描数据")
    snapshot = report_service.get_snapshot(
        project.project_id, ReportType.PROJECT_SUMMARY
    )
    assert snapshot.findings == ()
    assert snapshot.evidence == ()
    assert snapshot.tasks == ()
    assert snapshot.authorization.total_count == 0
    assert snapshot.stats is not None
    assert snapshot.stats.finding_count == 0
    assert set(snapshot.stats.severity_counts) == {item.value for item in Severity}
    assert snapshot.stats.evidence_type_counts["screenshot"] == 0
    assert any("没有扫描任务" in text for text in snapshot.warnings)
    assert any("没有 Finding" in text for text in snapshot.warnings)
    assert any("没有授权记录" in text for text in snapshot.warnings)
    assert any("不能据此推断不存在漏洞" in text for text in snapshot.warnings)


def test_missing_project_raises(report_service):
    with pytest.raises(NotFoundError):
        report_service.get_snapshot(999999, ReportType.VULNERABILITY)
    with pytest.raises(NotFoundError):
        report_service.get_snapshot(0, ReportType.VULNERABILITY)


def test_project_isolation(
    db,
    report_repo,
    report_service,
    local_project,
    seeded,
    projects,
    clock,
):
    other_source = Path(local_project.local_path + "_other")
    other_source.mkdir(parents=True, exist_ok=True)
    other = projects.create_project(
        "另一个项目", "local_audit", "隔离测试", str(other_source), "active"
    )
    other_finding = insert_finding(
        db,
        other.project_id,
        title="其他项目 Finding",
        scanner_name="bandit",
        rule_id="B999",
        metadata={"source": "fixture"},
    )
    _add = _add_evidence(
        db,
        other.project_id,
        other_finding,
        title="其他项目证据",
        description="不应出现在本地项目报告",
    )
    local_snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.PROJECT_SUMMARY
    )
    other_snapshot = report_service.get_snapshot(
        other.project_id, ReportType.PROJECT_SUMMARY
    )
    assert {item.finding_id for item in local_snapshot.findings}.isdisjoint(
        {other_finding}
    )
    assert {item.project_id for item in local_snapshot.findings} == {
        local_project.project_id
    }
    assert {item.project_id for item in other_snapshot.findings} == {
        other.project_id
    }
    assert {item.finding_id for item in other_snapshot.findings} == {other_finding}
    assert _add > 0
    assert all(
        item.evidence_id != _add for item in local_snapshot.evidence
    )


def test_authorization_summary(
    db, report_service, local_project, local_asset, authorizations, clock
):
    _confirmed_auth(authorizations, local_project, clock, source="有效授权")
    authorizations.create_authorization(
        local_project.project_id,
        authorization_source="待审核授权",
        authorization_document="C:/authorized/pending.pdf",
        start_time=clock.value - timedelta(days=1),
        end_time=clock.value + timedelta(days=30),
        authorization_status=AuthStatus.PENDING,
    )
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.PROJECT_SUMMARY
    )
    auth = snapshot.authorization
    assert auth.total_count == 2
    assert auth.confirmed_count == 1
    assert auth.pending_count == 1
    assert auth.effective_count == 1
    assert auth.has_effective_authorization is True
    assert auth.scope_asset_count == 1
    assert auth.active_scope_asset_count == 1
    assert auth.historical_scan_authorization_available is False
    assert "历史扫描" in auth.note


def test_missing_authorization_is_reported_not_invented(
    report_service, projects
):
    project = projects.create_project("无授权项目", "local_audit", "没有授权记录")
    snapshot = report_service.get_snapshot(
        project.project_id, ReportType.PROJECT_SUMMARY
    )
    assert snapshot.authorization.total_count == 0
    assert snapshot.authorization.effective_count == 0
    assert any("没有授权记录" in text for text in snapshot.warnings)
    assert any("不能作为授权完成证明" in text for text in snapshot.warnings)


def test_file_evidence_is_hashed_and_scoped(
    report_service, managed_root, local_project, seeded, db
):
    project_dir = managed_root / f"project_{local_project.project_id}"
    project_dir.mkdir(parents=True)
    file_path = project_dir / "report-evidence.png"
    file_path.write_bytes(b"phase6-report-evidence")
    digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="带文件证据的 Finding",
        scanner_name="bandit",
        rule_id="B999",
        metadata={"source": "fixture"},
    )
    evidence_id = _add_evidence(
        db,
        local_project.project_id,
        finding_id,
        evidence_type=EvidenceType.SCREENSHOT.value,
        title="报告截图",
        file_path=str(file_path),
        file_name=file_path.name,
        file_hash=digest,
    )
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.EVIDENCE
    )
    evidence = next(item for item in snapshot.evidence if item.evidence_id == evidence_id)
    assert evidence.file_exists is True
    assert evidence.hash_matches is True
    assert evidence.managed_path == f"project_{local_project.project_id}/{file_path.name}"
    assert snapshot.stats is not None
    assert snapshot.stats.file_evidence_count == 1
    assert snapshot.stats.missing_evidence_file_count == 0
    assert snapshot.stats.hash_mismatch_count == 0


def test_missing_and_outside_evidence_files_are_not_read(
    report_service, managed_root, local_project, local_asset, db, tmp_path
):
    project_dir = managed_root / f"project_{local_project.project_id}"
    project_dir.mkdir(parents=True)
    inside_missing = project_dir / "missing.png"
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"outside-secret")
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="缺失文件 Finding",
        scanner_name="bandit",
        rule_id="B999",
    )
    missing_id = _add_evidence(
        db,
        local_project.project_id,
        finding_id,
        file_path=str(inside_missing),
        file_name=inside_missing.name,
        file_hash="a" * 64,
    )
    outside_id = _add_evidence(
        db,
        local_project.project_id,
        finding_id,
        file_path=str(outside),
        file_name=outside.name,
        file_hash="b" * 64,
    )
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.EVIDENCE
    )
    missing = next(item for item in snapshot.evidence if item.evidence_id == missing_id)
    outside_item = next(
        item for item in snapshot.evidence if item.evidence_id == outside_id
    )
    assert missing.file_exists is False
    assert missing.hash_matches is None
    assert missing.managed_path == (
        f"project_{local_project.project_id}/{inside_missing.name}"
    )
    assert outside_item.file_exists is False
    assert outside_item.hash_matches is None
    assert outside_item.managed_path is None
    assert any("不在当前项目受管证据目录" in text for text in snapshot.warnings)
    assert any("受管文件不存在" in text for text in snapshot.warnings)


def test_text_evidence_has_no_file_status(
    report_service, local_project, local_asset, db
):
    finding_id = insert_finding(
        db,
        local_project.project_id,
        title="文本证据 Finding",
        scanner_name="bandit",
        rule_id="B999",
    )
    evidence_id = _add_evidence(
        db,
        local_project.project_id,
        finding_id,
        title="纯文本证据",
    )
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.EVIDENCE
    )
    item = next(item for item in snapshot.evidence if item.evidence_id == evidence_id)
    assert item.file_path == ""
    assert item.file_exists is None
    assert item.hash_matches is None
    assert item.managed_path is None


def test_report_request_and_artifact_stub(report_service, local_project):
    request = ReportRequest(
        project_id=local_project.project_id,
        report_type=ReportType.VULNERABILITY,
        report_format=ReportFormat.HTML,
        title="测试报告",
    )
    snapshot = report_service.get_snapshot_for_request(request)
    assert snapshot.report_type is ReportType.VULNERABILITY
    artifact = report_service.artifact_stub(request, snapshot)
    assert artifact.path is None
    assert artifact.sha256 is None
    assert artifact.snapshot_id == snapshot.snapshot_id
    assert artifact.report_format is ReportFormat.HTML
    with pytest.raises(ValidationError):
        report_service.get_snapshot(local_project.project_id, "not-a-type")


def test_dto_is_immutable(report_service, local_project):
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.PROJECT_SUMMARY
    )
    with pytest.raises(FrozenInstanceError):
        snapshot.findings = ()  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        snapshot.project.project_name = "changed"  # type: ignore[misc]
    if snapshot.stats is not None:
        with pytest.raises(TypeError):
            snapshot.stats.severity_counts["high"] = 99  # type: ignore[index]


def test_original_data_is_not_modified(
    db, report_service, local_project, seeded
):
    before = db.fetch_one(
        "SELECT COUNT(*) AS c, SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) "
        "AS open_count FROM findings WHERE project_id = ?",
        (local_project.project_id,),
    )
    before_evidence = db.fetch_one(
        "SELECT COUNT(*) AS c FROM evidence WHERE project_id = ?",
        (local_project.project_id,),
    )
    before_tasks = db.fetch_one(
        "SELECT COUNT(*) AS c FROM scan_tasks WHERE project_id = ?",
        (local_project.project_id,),
    )
    snapshot = report_service.get_snapshot(
        local_project.project_id, ReportType.PROJECT_SUMMARY
    )
    assert snapshot.stats is not None
    after = db.fetch_one(
        "SELECT COUNT(*) AS c, SUM(CASE WHEN status = 'open' THEN 1 ELSE 0 END) "
        "AS open_count FROM findings WHERE project_id = ?",
        (local_project.project_id,),
    )
    after_evidence = db.fetch_one(
        "SELECT COUNT(*) AS c FROM evidence WHERE project_id = ?",
        (local_project.project_id,),
    )
    after_tasks = db.fetch_one(
        "SELECT COUNT(*) AS c FROM scan_tasks WHERE project_id = ?",
        (local_project.project_id,),
    )
    assert dict(before) == dict(after)
    assert dict(before_evidence) == dict(after_evidence)
    assert dict(before_tasks) == dict(after_tasks)


def test_read_transaction_consistency_under_concurrent_write(
    db, report_repo, local_project, local_asset, clock
):
    insert_finding(
        db,
        local_project.project_id,
        title="并发快照初始 Finding",
        scanner_name="bandit",
        rule_id="B001",
        metadata={"source": "fixture"},
    )
    with db.connection() as connection:
        connection.execute("BEGIN")
        try:
            before = report_repo._build_snapshot(  # noqa: SLF001
                connection,
                local_project.project_id,
                ReportType.VULNERABILITY,
                clock.value,
            )
            insert_finding(
                db,
                local_project.project_id,
                title="并发写入的新 Finding",
                scanner_name="bandit",
                rule_id="B002",
                metadata={"source": "fixture"},
            )
            after = report_repo._build_snapshot(  # noqa: SLF001
                connection,
                local_project.project_id,
                ReportType.VULNERABILITY,
                clock.value,
            )
        finally:
            connection.rollback()
    outside = report_repo.load_snapshot(
        local_project.project_id, ReportType.VULNERABILITY, generated_at=clock.value
    )
    assert len(before.findings) == 1
    assert len(after.findings) == 1
    assert len(outside.findings) == 2
    assert before.findings[0].finding_id == after.findings[0].finding_id


def test_connection_is_released_after_error(
    db, report_repo, local_project, monkeypatch, clock
):
    def fail(*args, **kwargs):
        raise RuntimeError("forced snapshot failure")

    monkeypatch.setattr(report_repo, "_build_snapshot", fail)
    with pytest.raises(RuntimeError):
        report_repo.load_snapshot(
            local_project.project_id, ReportType.VULNERABILITY, generated_at=clock.value
        )
    db.execute("CREATE TABLE _report_probe (id INTEGER)")
    assert db.fetch_one(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name = '_report_probe'"
    ) is not None


def test_stats_zero_is_not_missing_data(report_service, projects):
    project = projects.create_project("零值项目", "local_audit", "零值统计")
    snapshot = report_service.get_snapshot(
        project.project_id, ReportType.PROJECT_SUMMARY
    )
    stats = snapshot.stats
    assert stats is not None
    assert stats.task_status_counts["completed"] == 0
    assert stats.finding_status_counts["open"] == 0
    assert stats.severity_counts["high"] == 0
    assert stats.evidence_type_counts["other_file"] == 0
    assert stats.task_scanner_counts == {}


def test_snapshot_warnings_do_not_claim_scan_success(report_service, projects):
    project = projects.create_project("空扫描项目", "local_audit", "空扫描")
    snapshot = report_service.get_snapshot(
        project.project_id, ReportType.VULNERABILITY
    )
    assert any("不能据此推断扫描通过" in text for text in snapshot.warnings)
    assert any("不能据此推断不存在漏洞" in text for text in snapshot.warnings)
    assert "扫描通过" not in snapshot.data_scope
