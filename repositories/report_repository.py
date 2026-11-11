"""Read-only, project-scoped report snapshot repository."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime
from types import MappingProxyType
from typing import Any

from core.errors import NotFoundError, StorageError
from core.models import (
    Authorization,
    Evidence,
    Finding,
    Project,
    ScanTask,
    ScopeAsset,
)
from core.models.enums import AuthStatus, FindingStatus
from core.timeutil import ensure_aware_utc, utc_now
from core.models.report import (
    ReportAuthorizationSummary,
    ReportEvidence,
    ReportFinding,
    ReportSnapshot,
    ReportTaskSummary,
    ReportType,
)
from database.connection import Database

_SAFE_METADATA_KEYS = frozenset(
    {
        "dependency_name",
        "current_version",
        "vulnerability_id",
        "aliases",
        "affected_versions",
        "fix_versions",
        "source",
        "vulnerability_service",
        "dependency_file",
        "file_type",
        "severity_source",
        "bandit_test_id",
        "semgrep_check_id",
    }
)

_PROJECT_SQL = (
    "SELECT project_id, project_name, project_type, description, local_path, "
    "status, created_at, updated_at FROM projects WHERE project_id = ?"
)
_AUTHORIZATION_SQL = (
    "SELECT authorization_id, project_id, authorization_source, "
    "authorization_document, start_time, end_time, authorization_status, notes, "
    "created_at, updated_at FROM authorizations WHERE project_id = ? "
    "ORDER BY created_at DESC, authorization_id DESC"
)
_SCOPE_ASSET_SQL = (
    "SELECT asset_id, project_id, asset_type, asset_value, authorization_id, "
    "allowed_operations, asset_status, notes, created_at, updated_at "
    "FROM scope_assets WHERE project_id = ? ORDER BY asset_id ASC"
)
_TASK_SQL = (
    "SELECT task_id, project_id, task_type, target, status, started_at, "
    "finished_at, result_summary, created_at, current_scanner, progress, "
    "error_message, scanners_json, cancel_requested, cancelled_at "
    "FROM scan_tasks WHERE project_id = ? ORDER BY created_at DESC, task_id DESC"
)
_FINDING_SQL = (
    "SELECT f.finding_id, f.project_id, f.task_id, f.title, f.category, "
    "f.risk_level, f.affected_scope, f.description, f.remediation, f.status, "
    "f.created_at, f.updated_at, f.confidence, f.file_path, f.line_number, "
    "f.rule_id, f.scanner_name, f.scanner_version, f.detected_at, "
    "f.metadata_json, f.manual_notes, f.status_changed_at, f.last_seen_at, "
    "p.project_name AS project_name, "
    "(SELECT COUNT(*) FROM evidence e WHERE e.project_id = f.project_id "
    " AND e.finding_id = f.finding_id) AS evidence_count "
    "FROM findings f JOIN projects p ON p.project_id = f.project_id "
    "WHERE f.project_id = ? "
    "ORDER BY CASE f.risk_level WHEN 'critical' THEN 5 WHEN 'high' THEN 4 "
    "WHEN 'medium' THEN 3 WHEN 'low' THEN 2 ELSE 1 END DESC, "
    "COALESCE(f.detected_at, f.created_at) DESC, f.finding_id DESC"
)
_EVIDENCE_SQL = (
    "SELECT e.evidence_id, e.project_id, e.finding_id, e.evidence_type, e.title, "
    "e.description, e.file_path, e.file_name, e.sha256, e.captured_at, e.source, "
    "e.created_at, p.project_name AS project_name, "
    "f.title AS finding_title "
    "FROM evidence e JOIN projects p ON p.project_id = e.project_id "
    "LEFT JOIN findings f ON f.finding_id = e.finding_id "
    "WHERE e.project_id = ? ORDER BY e.created_at DESC, e.evidence_id DESC"
)


class ReportRepository:
    """Builds one immutable report snapshot from one read transaction."""

    def __init__(self, database: Database, clock=utc_now) -> None:
        self._db = database
        self._clock = clock

    def load_snapshot(
        self,
        project_id: int,
        report_type: ReportType = ReportType.PROJECT_SUMMARY,
        *,
        generated_at: datetime | None = None,
    ) -> ReportSnapshot:
        if int(project_id) <= 0:
            raise NotFoundError("项目不存在")
        moment = ensure_aware_utc(generated_at or self._clock())
        try:
            with self._db.connection() as connection:
                # SQLite has no BEGIN READ ONLY form; query_only is the
                # enforceable read-only guard for this connection.
                connection.execute("PRAGMA query_only = ON")
                connection.execute("BEGIN")
                try:
                    return self._build_snapshot(
                        connection, int(project_id), report_type, moment
                    )
                finally:
                    try:
                        connection.rollback()
                    except sqlite3.Error:
                        pass
        except sqlite3.Error as exc:
            raise StorageError(f"报告快照读取失败: {exc}") from exc

    def _build_snapshot(
        self,
        connection: sqlite3.Connection,
        project_id: int,
        report_type: ReportType,
        generated_at: datetime,
    ) -> ReportSnapshot:
        project_row = connection.execute(_PROJECT_SQL, (project_id,)).fetchone()
        if project_row is None:
            raise NotFoundError("项目不存在")
        project = Project.from_row(project_row)

        authorization_rows = connection.execute(
            _AUTHORIZATION_SQL, (project_id,)
        ).fetchall()
        asset_rows = connection.execute(_SCOPE_ASSET_SQL, (project_id,)).fetchall()
        task_rows = connection.execute(_TASK_SQL, (project_id,)).fetchall()
        finding_rows = connection.execute(_FINDING_SQL, (project_id,)).fetchall()
        evidence_rows = connection.execute(_EVIDENCE_SQL, (project_id,)).fetchall()

        authorizations = [Authorization.from_row(row) for row in authorization_rows]
        assets = [ScopeAsset.from_row(row) for row in asset_rows]
        tasks = tuple(_task_summary(ScanTask.from_row(row)) for row in task_rows)
        findings = tuple(
            _finding_item(Finding.from_row(row)) for row in finding_rows
        )
        evidence = tuple(
            _evidence_item(Evidence.from_row(row)) for row in evidence_rows
        )

        status_counts = {
            status: sum(
                1 for item in authorizations if item.authorization_status is status
            )
            for status in AuthStatus
        }
        effective = sum(1 for item in authorizations if item.is_effective(generated_at))
        active_assets = sum(
            1 for item in assets if item.asset_status.value == "active"
        )
        authorization = ReportAuthorizationSummary(
            as_of=generated_at,
            total_count=len(authorizations),
            effective_count=effective,
            confirmed_count=status_counts[AuthStatus.CONFIRMED],
            expired_count=status_counts[AuthStatus.EXPIRED],
            pending_count=status_counts[AuthStatus.PENDING],
            revoked_count=status_counts[AuthStatus.REVOKED],
            scope_asset_count=len(assets),
            active_scope_asset_count=active_assets,
            historical_scan_authorization_available=False,
            note=(
                "当前授权摘要按报告生成时刻计算；数据库未保存扫描时授权快照，"
                "不能将当前授权状态等同于历史扫描时的授权状态。"
            ),
        )

        schema_row = connection.execute("PRAGMA user_version").fetchone()
        schema_version = int(schema_row[0]) if schema_row else 0
        return ReportSnapshot(
            snapshot_id=uuid.uuid4().hex,
            report_type=report_type,
            project=project,
            authorization=authorization,
            tasks=tasks,
            findings=findings,
            evidence=evidence,
            stats=None,
            generated_at=generated_at,
            schema_version=schema_version,
            data_scope=(),
            warnings=(),
            known_limitations=(),
        )


def _task_summary(task: ScanTask) -> ReportTaskSummary:
    return ReportTaskSummary(
        task_id=task.task_id,
        project_id=task.project_id,
        task_type=task.task_type,
        target=task.target,
        status=task.status,
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_at=task.created_at,
        result_summary=task.result_summary,
        error_message=task.error_message,
        progress=task.progress,
        scanners=task.scanners,
        current_scanner=task.current_scanner,
    )


def _finding_item(finding: Finding) -> ReportFinding:
    metadata = finding.metadata if isinstance(finding.metadata, dict) else {}
    filtered = {
        key: _freeze_value(metadata[key])
        for key in _SAFE_METADATA_KEYS
        if key in metadata and _metadata_value_safe(metadata[key])
    }
    fix_versions_raw = metadata.get("fix_versions")
    fix_versions = (
        tuple(str(item) for item in fix_versions_raw if str(item).strip())
        if isinstance(fix_versions_raw, (list, tuple))
        else ()
    )
    dependency_name = _optional_text(metadata.get("dependency_name"))
    current_version = _optional_text(metadata.get("current_version"))
    vulnerability_id = _optional_text(metadata.get("vulnerability_id"))
    affected_versions = _optional_text(metadata.get("affected_versions"))
    severity_source = _optional_text(metadata.get("severity_source")) or "scanner"
    return ReportFinding(
        finding_id=finding.finding_id or 0,
        project_id=finding.project_id or 0,
        task_id=finding.task_id,
        title=finding.title,
        category=finding.category,
        description=finding.description,
        severity=finding.severity,
        severity_source=severity_source,
        confidence=finding.confidence,
        scanner_name=finding.scanner_name,
        scanner_version=finding.scanner_version,
        rule_id=finding.rule_id,
        file_path=finding.file_path,
        line_number=finding.line_number,
        recommendation=finding.recommendation,
        status=FindingStatus.from_external(finding.status),
        manual_notes=finding.manual_notes,
        detected_at=finding.detected_at,
        last_seen_at=finding.last_seen or finding.detected_at,
        dependency_name=dependency_name,
        dependency_version=current_version,
        vulnerability_id=vulnerability_id,
        fix_versions=fix_versions,
        affected_versions=affected_versions,
        evidence_count=finding.evidence_count,
        metadata=MappingProxyType(filtered),
        raw_metadata_omitted=len(filtered) != len(metadata),
    )


def _evidence_item(evidence: Evidence) -> ReportEvidence:
    return ReportEvidence(
        evidence_id=evidence.evidence_id,
        project_id=evidence.project_id,
        finding_id=evidence.finding_id,
        finding_title=evidence.finding_title,
        evidence_type=evidence.evidence_type,
        title=evidence.title,
        description=evidence.description,
        file_name=evidence.file_name,
        source=evidence.source,
        file_path=evidence.file_path,
        managed_path=None,
        file_hash=evidence.file_hash,
        captured_at=evidence.captured_at,
        created_at=evidence.created_at,
        file_exists=None,
        hash_matches=None,
        file_status_note="",
    )


def _metadata_value_safe(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, (list, tuple)):
        return all(isinstance(item, (str, int, float, bool)) for item in value)
    return False


def _freeze_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_value(item) for item in value)
    return value


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
