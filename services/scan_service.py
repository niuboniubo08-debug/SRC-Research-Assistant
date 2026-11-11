"""Source-audit orchestration: validation, scanners, tasks and findings."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterable, Sequence

from core.errors import NotFoundError, StorageError, ValidationError
from core.models import (
    Confidence,
    Finding,
    ScanTask,
    ScanTaskStatus,
    ScanTaskType,
    Severity,
)
from core.timeutil import to_db_time, utc_now
from database.connection import Database
from scanners.base import (
    BaseScanner,
    ScanCancelled,
    ScannerError,
    ScannerTimeoutError,
    ScanOptions,
)
from security.scope_validator import ScopeValidator
from services.audit_service import AuditLogService
from services.project_service import ProjectService

ProgressCallback = Callable[[int, str, str], None]


@dataclass(frozen=True, slots=True)
class ScannerInfo:
    name: str
    display_name: str
    available: bool
    version: str
    reason: str
    command: str


@dataclass(slots=True)
class ScanOutcome:
    task: ScanTask
    findings: tuple[Finding, ...]
    warnings: tuple[str, ...]
    errors: tuple[str, ...]
    scanners_run: tuple[str, ...]
    scanners_skipped: tuple[str, ...]

    @property
    def cancelled(self) -> bool:
        return self.task.status is ScanTaskStatus.CANCELLED

    @property
    def failed(self) -> bool:
        return self.task.status is ScanTaskStatus.FAILED

    @property
    def success(self) -> bool:
        return self.task.status is ScanTaskStatus.COMPLETED


class ScanService:
    """Coordinates local-only source audits through existing services."""

    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        scope_validator: ScopeValidator,
        project_service: ProjectService,
        scanners: Sequence[BaseScanner],
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._validator = scope_validator
        self._projects = project_service
        self._clock = clock
        self._scanners: dict[str, BaseScanner] = {}
        for scanner in scanners:
            if scanner.name in self._scanners:
                raise ValueError(f"扫描器名称重复: {scanner.name}")
            if not scanner.name:
                raise ValueError("扫描器必须有 name")
            self._scanners[scanner.name] = scanner

    # ------------------------------------------------------------------ status
    def scanner_infos(self, refresh: bool = False) -> list[ScannerInfo]:
        infos: list[ScannerInfo] = []
        for scanner in self._scanners.values():
            availability = scanner.is_available(refresh=refresh)
            infos.append(
                ScannerInfo(
                    name=scanner.name,
                    display_name=scanner.display_name,
                    available=availability.available,
                    version=availability.version,
                    reason=availability.reason,
                    command=availability.command,
                )
            )
        return infos

    @property
    def scanner_names(self) -> tuple[str, ...]:
        return tuple(self._scanners)

    # ------------------------------------------------------------------ validation
    def _validate_target(
        self, project_id: int, scanner_names: Iterable[str]
    ) -> tuple[str, tuple[str, ...]]:
        project = self._projects.get_project(project_id)
        target = project.local_path.strip()
        if not target:
            raise ValidationError("当前项目未配置本地代码路径")
        decision = self._validator.check_local_path(
            project.project_id, target, operation="source_audit"
        )
        if not decision.allowed:
            raise ValidationError(f"本地路径校验失败：{decision.reason}")
        names = [name for name in scanner_names if name]
        if not names:
            raise ValidationError("至少需要选择一个扫描器")
        unknown = [name for name in names if name not in self._scanners]
        if unknown:
            raise ValidationError(f"未知扫描器: {', '.join(unknown)}")
        # Preserve registry order while removing duplicates.
        requested = tuple(name for name in self._scanners if name in set(names))
        return decision.target, requested

    # ------------------------------------------------------------------ public
    def run_scan(
        self,
        project_id: int,
        scanner_names: Sequence[str] | None = None,
        *,
        timeout_seconds: float = 180.0,
        cancel_event: threading.Event | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ScanOutcome:
        names = self.scanner_names if scanner_names is None else tuple(scanner_names)
        target, requested = self._validate_target(project_id, names)
        cancel = cancel_event or threading.Event()
        if timeout_seconds <= 0:
            raise ValidationError("扫描超时时间必须大于 0")

        task_id = self._create_task(project_id, target, requested)
        task = self._get_task(project_id, task_id)

        availability: dict[str, Any] = {}
        for name in requested:
            availability[name] = self._scanners[name].is_available()
        available = [name for name in requested if availability[name].available]
        skipped = [name for name in requested if not availability[name].available]
        warnings = [
            f"{self._scanners[name].display_name} 不可用：{availability[name].reason}"
            for name in skipped
        ]

        if cancel.is_set():
            return self._finalize(
                project_id,
                task_id,
                ScanTaskStatus.CANCELLED,
                (),
                tuple(warnings),
                (),
                (),
                tuple(skipped),
                cancelled=True,
                progress=0,
            )
        if not available:
            errors = ["所选扫描器均不可用，未执行扫描"]
            return self._finalize(
                project_id,
                task_id,
                ScanTaskStatus.FAILED,
                (),
                tuple(warnings),
                tuple(errors),
                (),
                tuple(skipped),
                progress=0,
            )

        self._mark_running(project_id, task_id)
        progress_value = self._report(
            progress_callback, 3, "初始化扫描", "", project_id, task_id
        )
        findings_saved: list[Finding] = []
        errors: list[str] = []
        scanners_run: list[str] = []
        cancelled = False
        try:
            for index, name in enumerate(available):
                if cancel.is_set():
                    cancelled = True
                    break
                scanner = self._scanners[name]
                start_percent = 5 + int((index / len(available)) * 85)
                progress_value = self._report(
                    progress_callback,
                    start_percent,
                    f"正在运行 {scanner.display_name}",
                    name,
                    project_id,
                    task_id,
                )
                try:
                    output = scanner.scan(
                        target,
                        ScanOptions(
                            timeout_seconds=float(timeout_seconds),
                            cancel_event=cancel,
                        ),
                    )
                except ScanCancelled:
                    cancelled = True
                    break
                except ScannerTimeoutError as exc:
                    errors.append(f"{scanner.display_name} 超时：{exc}")
                except ScannerError as exc:
                    errors.append(f"{scanner.display_name} 失败：{exc}")
                except Exception as exc:  # noqa: BLE001 - scanner boundary must not crash task
                    errors.append(f"{scanner.display_name} 内部错误：{exc}")
                else:
                    scanners_run.append(scanner.name)
                    warnings.extend(output.warnings)
                    saved = self._save_findings(
                        project_id, task_id, target, output.findings
                    )
                    findings_saved.extend(saved)
                if cancel.is_set():
                    cancelled = True
                    break
                done_percent = 5 + int(((index + 1) / len(available)) * 85)
                progress_value = self._report(
                    progress_callback,
                    done_percent,
                    f"{scanner.display_name} 已完成",
                    name,
                    project_id,
                    task_id,
                )
        except Exception as exc:  # noqa: BLE001 - ensure terminal task state
            errors.append(f"扫描流程异常：{exc}")

        if cancelled or cancel.is_set():
            return self._finalize(
                project_id,
                task_id,
                ScanTaskStatus.CANCELLED,
                tuple(findings_saved),
                tuple(warnings),
                tuple(errors),
                tuple(scanners_run),
                tuple(skipped),
                cancelled=True,
                progress=progress_value,
            )
        if errors:
            return self._finalize(
                project_id,
                task_id,
                ScanTaskStatus.FAILED,
                tuple(findings_saved),
                tuple(warnings),
                tuple(errors),
                tuple(scanners_run),
                tuple(skipped),
                progress=100,
            )
        return self._finalize(
            project_id,
            task_id,
            ScanTaskStatus.COMPLETED,
            tuple(findings_saved),
            tuple(warnings),
            (),
            tuple(scanners_run),
            tuple(skipped),
            progress=100,
        )

    # ------------------------------------------------------------------ task sql
    def _create_task(self, project_id: int, target: str, scanners: tuple[str, ...]) -> int:
        now = to_db_time(self._clock())
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_tasks "
                "(project_id, task_type, target, status, created_at, progress, scanners_json) "
                "VALUES (?, 'source_audit', ?, 'pending', ?, 0, ?)",
                (project_id, target, now, json.dumps(list(scanners), ensure_ascii=False)),
            )
            task_id = int(cursor.lastrowid or 0)
            self._audit.record(
                event_type="source_scan_started",
                target=target,
                operation="source_audit",
                decision="info",
                message=f"创建源代码审计任务 #{task_id}",
                details={"task_id": task_id, "scanners": list(scanners)},
                project_id=project_id,
                task_id=task_id,
                conn=conn,
                created_at=self._clock(),
            )
        return task_id

    def _mark_running(self, project_id: int, task_id: int) -> None:
        now = to_db_time(self._clock())
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE scan_tasks SET status = 'running', started_at = ?, "
                "current_scanner = '', progress = 2, error_message = '' "
                "WHERE task_id = ? AND project_id = ?",
                (now, task_id, project_id),
            )

    def _report(
        self,
        callback: ProgressCallback | None,
        percent: int,
        message: str,
        scanner_name: str,
        project_id: int,
        task_id: int,
    ) -> int:
        safe_percent = max(0, min(100, int(percent)))
        now = to_db_time(self._clock())
        try:
            self._db.execute(
                "UPDATE scan_tasks SET progress = ?, current_scanner = ? "
                "WHERE task_id = ? AND project_id = ?",
                (safe_percent, scanner_name, task_id, project_id),
            )
        except StorageError:
            # The final terminal update will surface persistent storage failure.
            pass
        if callback is not None:
            try:
                callback(safe_percent, message, scanner_name)
            except Exception:
                pass
        return safe_percent

    def _finalize(
        self,
        project_id: int,
        task_id: int,
        status: ScanTaskStatus,
        findings: tuple[Finding, ...],
        warnings: tuple[str, ...],
        errors: tuple[str, ...],
        scanners_run: tuple[str, ...],
        scanners_skipped: tuple[str, ...],
        *,
        cancelled: bool = False,
        progress: int = 100,
    ) -> ScanOutcome:
        now = self._clock()
        stamp = to_db_time(now)
        if status is ScanTaskStatus.COMPLETED:
            summary = self._summary(findings, scanners_run, scanners_skipped, warnings)
            error_message = ""
            event_type = "source_scan_completed"
            decision = "info"
        elif status is ScanTaskStatus.CANCELLED:
            summary = (
                f"扫描已取消；已保留 {len(findings)} 个结果。"
                + self._summary(findings, scanners_run, scanners_skipped, warnings)
            )
            error_message = "用户取消扫描"
            event_type = "source_scan_cancelled"
            decision = "info"
        else:
            summary = (
                f"扫描失败；已保留 {len(findings)} 个结果。"
                + self._summary(findings, scanners_run, scanners_skipped, warnings)
            )
            error_message = "；".join(errors) or "扫描失败"
            event_type = "source_scan_failed"
            decision = "error"
        with self._db.transaction() as conn:
            conn.execute(
                "UPDATE scan_tasks SET status = ?, finished_at = ?, progress = ?, "
                "current_scanner = '', result_summary = ?, error_message = ?, "
                "cancel_requested = ?, cancelled_at = ? "
                "WHERE task_id = ? AND project_id = ?",
                (
                    status.value,
                    stamp,
                    max(0, min(100, int(progress))),
                    summary,
                    error_message,
                    1 if cancelled else 0,
                    stamp if cancelled else None,
                    task_id,
                    project_id,
                ),
            )
            self._audit.record(
                event_type=event_type,
                target=str(findings[0].affected_scope) if findings else "",
                operation="source_audit",
                decision=decision,
                message=f"源代码审计任务 #{task_id} {status.label}",
                details={
                    "task_id": task_id,
                    "status": status.value,
                    "findings": len(findings),
                    "scanners_run": list(scanners_run),
                    "scanners_skipped": list(scanners_skipped),
                    "warnings": list(warnings)[:20],
                    "errors": list(errors)[:20],
                },
                project_id=project_id,
                task_id=task_id,
                conn=conn,
                created_at=now,
            )
        task = self._get_task(project_id, task_id)
        stored = self.list_findings(project_id, task_id=task_id, limit=5000)
        return ScanOutcome(
            task=task,
            findings=tuple(stored),
            warnings=tuple(warnings),
            errors=tuple(errors),
            scanners_run=tuple(scanners_run),
            scanners_skipped=tuple(scanners_skipped),
        )

    @staticmethod
    def _summary(
        findings: tuple[Finding, ...],
        scanners_run: tuple[str, ...],
        scanners_skipped: tuple[str, ...],
        warnings: tuple[str, ...],
    ) -> str:
        if findings:
            core = f"完成 {len(scanners_run)} 个扫描器，发现 {len(findings)} 个问题。"
        else:
            core = f"完成 {len(scanners_run)} 个扫描器，未发现匹配的安全问题。"
        if scanners_skipped:
            core += f" 跳过 {len(scanners_skipped)} 个不可用扫描器。"
        if warnings:
            core += f" 有 {len(warnings)} 条提示。"
        return core

    def _save_findings(
        self,
        project_id: int,
        task_id: int,
        target: str,
        findings: Iterable[Finding],
    ) -> list[Finding]:
        saved: list[Finding] = []
        now = self._clock()
        stamp = to_db_time(now)
        with self._db.transaction() as conn:
            for finding in findings:
                item = replace(
                    finding,
                    project_id=project_id,
                    task_id=task_id,
                    affected_scope=target,
                    finding_id=None,
                    created_at=now,
                    updated_at=now,
                )
                cursor = conn.execute(
                    "INSERT INTO findings "
                    "(project_id, task_id, title, category, risk_level, affected_scope, "
                    "description, remediation, status, created_at, updated_at, confidence, "
                    "file_path, line_number, rule_id, scanner_name, scanner_version, detected_at, "
                    "metadata_json, last_seen_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        project_id,
                        task_id,
                        item.title,
                        item.category,
                        item.severity.value,
                        target,
                        item.description,
                        item.recommendation,
                        stamp,
                        stamp,
                        item.confidence.value,
                        item.file_path,
                        max(0, int(item.line_number)),
                        item.rule_id,
                        item.scanner_name,
                        item.scanner_version,
                        to_db_time(item.detected_at),
                        json.dumps(item.metadata, ensure_ascii=False, sort_keys=True),
                        to_db_time(item.detected_at),
                    ),
                )
                saved.append(
                    replace(item, finding_id=int(cursor.lastrowid or 0))
                )
        return saved

    def _get_task(self, project_id: int, task_id: int) -> ScanTask:
        row = self._db.fetch_one(
            "SELECT * FROM scan_tasks WHERE task_id = ? AND project_id = ?",
            (task_id, project_id),
        )
        if row is None:
            raise NotFoundError("扫描任务不存在或不属于当前项目")
        return ScanTask.from_row(row)

    # ------------------------------------------------------------------ queries
    def get_task(self, project_id: int, task_id: int) -> ScanTask:
        return self._get_task(project_id, task_id)

    def list_tasks(self, project_id: int, limit: int = 50) -> list[ScanTask]:
        safe_limit = max(1, min(int(limit), 500))
        rows = self._db.fetch_all(
            "SELECT * FROM scan_tasks WHERE project_id = ? "
            "ORDER BY created_at DESC, task_id DESC LIMIT ?",
            (project_id, safe_limit),
        )
        return [ScanTask.from_row(row) for row in rows]

    def latest_task(self, project_id: int) -> ScanTask | None:
        row = self._db.fetch_one(
            "SELECT * FROM scan_tasks WHERE project_id = ? "
            "ORDER BY created_at DESC, task_id DESC LIMIT 1",
            (project_id,),
        )
        return ScanTask.from_row(row) if row else None

    def list_findings(
        self,
        project_id: int,
        *,
        task_id: int | None = None,
        severity: Severity | str | None = None,
        scanner_name: str | None = None,
        limit: int = 1000,
    ) -> list[Finding]:
        clauses = ["project_id = ?"]
        params: list[Any] = [project_id]
        if task_id is not None:
            clauses.append("task_id = ?")
            params.append(task_id)
        if severity is not None:
            try:
                severity_value = (
                    severity if isinstance(severity, Severity) else Severity(str(severity))
                )
            except ValueError as exc:
                raise ValidationError("风险等级筛选值无效") from exc
            clauses.append("risk_level = ?")
            params.append(severity_value.value)
        if scanner_name:
            clauses.append("scanner_name = ?")
            params.append(scanner_name)
        safe_limit = max(1, min(int(limit), 5000))
        rows = self._db.fetch_all(
            f"SELECT * FROM findings WHERE {' AND '.join(clauses)} "
            "ORDER BY CASE risk_level "
            "WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 "
            "WHEN 'low' THEN 2 ELSE 1 END DESC, file_path ASC, line_number ASC "
            "LIMIT ?",
            (*params, safe_limit),
        )
        return [Finding.from_row(row) for row in rows]

    def count_findings(
        self, project_id: int, *, task_id: int | None = None
    ) -> int:
        if task_id is None:
            row = self._db.fetch_one(
                "SELECT COUNT(*) AS count FROM findings WHERE project_id = ?",
                (project_id,),
            )
        else:
            row = self._db.fetch_one(
                "SELECT COUNT(*) AS count FROM findings WHERE project_id = ? AND task_id = ?",
                (project_id, task_id),
            )
        return int(row["count"]) if row else 0
