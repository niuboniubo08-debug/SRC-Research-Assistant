"""Local dependency discovery and pip-audit orchestration."""

from __future__ import annotations

import json
import re
import shutil
import threading
import tomllib
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable, Iterator, Sequence

from core.errors import NotFoundError, ValidationError
from core.models import Finding, ScanTask, ScanTaskStatus
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
_REQ_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9_.-]*)")


@dataclass(frozen=True, slots=True)
class DependencyFileInfo:
    path: Path
    relative_path: str
    kind: str
    dependency_count: int
    supported: bool
    reason: str = ""

    @property
    def display_name(self) -> str:
        return self.relative_path


@dataclass(frozen=True, slots=True)
class DependencyDiscovery:
    project_id: int
    project_name: str
    root: Path
    files: tuple[DependencyFileInfo, ...]
    primary: DependencyFileInfo | None
    message: str


@dataclass(frozen=True, slots=True)
class DependencyScannerInfo:
    name: str
    display_name: str
    available: bool
    version: str
    reason: str
    command: str


@dataclass(slots=True)
class DependencyAuditOutcome:
    task: ScanTask
    findings: tuple[Finding, ...]
    dependency_file: str
    audited_dependencies: int
    warnings: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def cancelled(self) -> bool:
        return self.task.status is ScanTaskStatus.CANCELLED

    @property
    def failed(self) -> bool:
        return self.task.status is ScanTaskStatus.FAILED

    @property
    def success(self) -> bool:
        return self.task.status is ScanTaskStatus.COMPLETED


class DependencyAuditService:
    """Coordinates local dependency discovery and pip-audit execution."""

    def __init__(
        self,
        database: Database,
        audit: AuditLogService,
        scope_validator: ScopeValidator,
        project_service: ProjectService,
        scanner: BaseScanner,
        work_dir: str | Path,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._audit = audit
        self._validator = scope_validator
        self._projects = project_service
        self._scanner = scanner
        self._work_dir = Path(work_dir)
        self._clock = clock

    # ------------------------------------------------------------------ discovery
    def scanner_info(self, refresh: bool = False) -> DependencyScannerInfo:
        availability = self._scanner.is_available(refresh=refresh)
        return DependencyScannerInfo(
            name=self._scanner.name,
            display_name=self._scanner.display_name,
            available=availability.available,
            version=availability.version,
            reason=availability.reason,
            command=availability.command,
        )

    def discover(self, project_id: int) -> DependencyDiscovery:
        project = self._projects.get_project(project_id)
        raw_path = project.local_path.strip()
        if not raw_path:
            raise ValidationError("当前项目未配置本地代码路径")
        decision = self._validator.check_local_path(
            project.project_id, raw_path, operation="dependency_audit"
        )
        if not decision.allowed:
            raise ValidationError(f"本地路径校验失败：{decision.reason}")
        root = Path(decision.target)
        files: list[DependencyFileInfo] = []
        for name, kind in (
            ("requirements.txt", "requirements"),
            ("pyproject.toml", "pyproject"),
        ):
            candidate = root / name
            if not candidate.exists():
                continue
            if candidate.is_symlink():
                files.append(
                    DependencyFileInfo(
                        candidate,
                        name,
                        kind,
                        0,
                        False,
                        "依赖文件是符号链接，拒绝读取项目范围外内容",
                    )
                )
                continue
            try:
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(root.resolve())
            except (OSError, ValueError):
                files.append(
                    DependencyFileInfo(
                        candidate,
                        name,
                        kind,
                        0,
                        False,
                        "依赖文件路径不在授权项目根目录内",
                    )
                )
                continue
            if not resolved.is_file():
                continue
            if kind == "requirements":
                deps, reason = self._read_requirements(resolved)
            else:
                deps, reason = self._read_pyproject(resolved)
            files.append(
                DependencyFileInfo(
                    resolved,
                    name,
                    kind,
                    len(deps),
                    not reason and bool(deps),
                    reason or ("未发现依赖项" if not deps else ""),
                )
            )
        primary = next(
            (item for item in files if item.supported and item.kind == "requirements"),
            None,
        )
        if primary is None:
            primary = next(
                (item for item in files if item.supported and item.kind == "pyproject"),
                None,
            )
        if primary is None:
            if not files:
                message = "未发现可审计依赖：项目根目录没有 requirements.txt 或 pyproject.toml"
            elif any(item.dependency_count > 0 for item in files):
                message = "发现依赖文件，但没有可审计的有效依赖"
            else:
                message = "未发现可审计依赖；请检查依赖文件内容或格式"
        else:
            message = f"已识别依赖文件：{primary.relative_path}"
        return DependencyDiscovery(
            project_id=project.project_id,
            project_name=project.project_name,
            root=root,
            files=tuple(files),
            primary=primary,
            message=message,
        )

    @staticmethod
    def _read_requirements(path: Path) -> tuple[list[str], str]:
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError as exc:
            return [], f"无法读取 requirements.txt：{exc}"
        deps: list[str] = []
        for line in lines:
            text = line.strip()
            if not text or text.startswith("#"):
                continue
            if text.startswith("-"):
                continue
            deps.append(text)
        return deps, ""

    @staticmethod
    def _read_pyproject(path: Path) -> tuple[list[str], str]:
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            return [], f"pyproject.toml 解析失败：{exc}"
        project = data.get("project")
        if not isinstance(project, dict):
            return [], "pyproject.toml 缺少 [project] 配置"
        dependencies = project.get("dependencies")
        if not isinstance(dependencies, list):
            return [], "pyproject.toml 缺少 [project].dependencies"
        deps = [str(item).strip() for item in dependencies if str(item).strip()]
        return deps, ""

    # ------------------------------------------------------------------ audit
    def run_audit(
        self,
        project_id: int,
        dependency_path: str | Path | None = None,
        *,
        timeout_seconds: float = 180.0,
        cancel_event: threading.Event | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> DependencyAuditOutcome:
        discovery = self.discover(project_id)
        selected = self._select_file(discovery, dependency_path)
        if selected is None:
            raise ValidationError(discovery.message)
        if timeout_seconds <= 0:
            raise ValidationError("审计超时时间必须大于 0")
        cancel = cancel_event or threading.Event()
        task_id = self._create_task(discovery.project_id, selected.relative_path)
        if cancel.is_set():
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.CANCELLED,
                (), (), (), 0, (), cancelled=True, progress=0,
            )

        info = self.scanner_info()
        if not info.available:
            return self._finish(
                discovery,
                selected,
                task_id,
                ScanTaskStatus.FAILED,
                (),
                (),
                (f"pip-audit 不可用：{info.reason}",),
                0,
                (),
                progress=0,
            )

        self._mark_running(discovery.project_id, task_id)
        progress_value = self._report(
            progress_callback, 10, "准备依赖审计", discovery.project_id, task_id
        )
        try:
            with self._prepared_input(selected) as prepared:
                progress_value = self._report(
                    progress_callback, 30, "运行 pip-audit", discovery.project_id, task_id
                )
                output = self._scanner.scan(
                    prepared,
                    ScanOptions(
                        timeout_seconds=float(timeout_seconds),
                        cancel_event=cancel,
                    ),
                )
        except ScanCancelled:
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.CANCELLED,
                (), (), (), 0, (), cancelled=True, progress=progress_value,
            )
        except ScannerTimeoutError as exc:
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.FAILED,
                (), (), (str(exc),), 0, (), progress=100,
            )
        except ScannerError as exc:
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.FAILED,
                (), (), (str(exc),), 0, (), progress=100,
            )
        except (OSError, ValidationError) as exc:
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.FAILED,
                (), (), (str(exc),), 0, (), progress=100,
            )
        except Exception as exc:  # noqa: BLE001 - task must reach terminal state
            return self._finish(
                discovery, selected, task_id, ScanTaskStatus.FAILED,
                (), (), (f"依赖审计内部错误：{exc}",), 0, (), progress=100,
            )

        audited = int(output.metadata.get("audited_dependencies") or 0)
        if audited == 0:
            return self._finish(
                discovery,
                selected,
                task_id,
                ScanTaskStatus.FAILED,
                (),
                output.warnings,
                ("pip-audit 未审计到任何依赖，不能判定为无漏洞",),
                0,
                (),
                progress=100,
            )
        try:
            mapped = self._map_findings(discovery, selected, output.findings)
            saved = self._save_findings(discovery.project_id, task_id, mapped)
        except Exception as exc:  # noqa: BLE001 - terminal status must be durable
            return self._finish(
                discovery,
                selected,
                task_id,
                ScanTaskStatus.FAILED,
                (),
                output.warnings,
                (f"依赖审计结果保存失败：{exc}",),
                audited,
                (),
                progress=100,
            )
        warnings = list(output.warnings)
        summary = (
            f"已审计 {audited} 个依赖，发现 {len(saved)} 个唯一漏洞。"
            if saved
            else f"已审计 {audited} 个依赖，未发现已知漏洞。"
        )
        return self._finish(
            discovery,
            selected,
            task_id,
            ScanTaskStatus.COMPLETED,
            tuple(saved),
            tuple(warnings),
            (),
            audited,
            (),
            progress=100,
            summary=summary,
        )

    def _select_file(
        self, discovery: DependencyDiscovery, requested: str | Path | None
    ) -> DependencyFileInfo | None:
        if requested is None:
            return discovery.primary
        requested_path = Path(requested)
        if not requested_path.is_absolute():
            requested_path = discovery.root / requested_path
        requested_resolved = requested_path.resolve(strict=False)
        for item in discovery.files:
            if item.path.resolve(strict=False) == requested_resolved:
                if not item.supported:
                    raise ValidationError(item.reason or "所选依赖文件不可审计")
                return item
        raise ValidationError("所选依赖文件不在当前项目根目录的可审计文件列表中")

    @contextmanager
    def _prepared_input(self, selected: DependencyFileInfo) -> Iterator[Path]:
        if selected.kind == "requirements":
            yield selected.path
            return
        deps, reason = self._read_pyproject(selected.path)
        if reason:
            raise ValidationError(reason)
        self._work_dir.mkdir(parents=True, exist_ok=True)
        temp_dir = self._work_dir / f"pyproject-{uuid.uuid4().hex}"
        temp_dir.mkdir(parents=True)
        prepared = temp_dir / "requirements.txt"
        prepared.write_text("\n".join(deps) + "\n", encoding="utf-8")
        try:
            yield prepared
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------ mapping
    def _map_findings(
        self,
        discovery: DependencyDiscovery,
        selected: DependencyFileInfo,
        findings: Sequence[Finding],
    ) -> list[Finding]:
        line_map = (
            self._requirements_line_map(selected.path)
            if selected.kind == "requirements"
            else {}
        )
        mapped: list[Finding] = []
        for finding in findings:
            metadata = dict(finding.metadata)
            dependency_name = str(metadata.get("dependency_name") or "")
            line_number = line_map.get(self._normalize_dependency_name(dependency_name), 0)
            metadata["dependency_file"] = selected.relative_path
            metadata["file_type"] = selected.kind
            mapped.append(
                replace(
                    finding,
                    file_path=selected.relative_path,
                    line_number=line_number,
                    affected_scope=selected.relative_path,
                    metadata=metadata,
                )
            )
        return mapped

    @staticmethod
    def _requirements_line_map(path: Path) -> dict[str, int]:
        mapping: dict[str, int] = {}
        try:
            lines = path.read_text(encoding="utf-8-sig").splitlines()
        except OSError:
            return mapping
        for number, line in enumerate(lines, start=1):
            text = line.strip()
            if not text or text.startswith("#") or text.startswith("-"):
                continue
            match = _REQ_NAME_RE.match(text)
            if match:
                name = DependencyAuditService._normalize_dependency_name(match.group(1))
                mapping.setdefault(name, number)
        return mapping

    @staticmethod
    def _normalize_dependency_name(name: str) -> str:
        return re.sub(r"[-_.]+", "-", name.strip().lower())

    # ------------------------------------------------------------------ persistence
    def _create_task(self, project_id: int, target: str) -> int:
        now = to_db_time(self._clock())
        with self._db.transaction() as conn:
            cursor = conn.execute(
                "INSERT INTO scan_tasks "
                "(project_id, task_type, target, status, created_at, progress, scanners_json) "
                "VALUES (?, 'dependency_audit', ?, 'pending', ?, 0, ?)",
                (project_id, target, now, '["pip-audit"]'),
            )
            task_id = int(cursor.lastrowid or 0)
            self._audit.record(
                event_type="dependency_audit_started",
                target=target,
                operation="dependency_audit",
                decision="info",
                message=f"创建依赖漏洞审计任务 #{task_id}",
                details={"task_id": task_id, "scanner": self._scanner.name},
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
                "current_scanner = ?, progress = 5, error_message = '' "
                "WHERE task_id = ? AND project_id = ?",
                (now, self._scanner.display_name, task_id, project_id),
            )

    def _report(
        self,
        callback: ProgressCallback | None,
        percent: int,
        message: str,
        project_id: int,
        task_id: int,
    ) -> int:
        safe_percent = max(0, min(100, int(percent)))
        self._db.execute(
            "UPDATE scan_tasks SET progress = ?, current_scanner = ? "
            "WHERE task_id = ? AND project_id = ?",
            (safe_percent, self._scanner.display_name, task_id, project_id),
        )
        if callback is not None:
            try:
                callback(safe_percent, message, self._scanner.display_name)
            except Exception:
                pass
        return safe_percent

    def _finish(
        self,
        discovery: DependencyDiscovery,
        selected: DependencyFileInfo,
        task_id: int,
        status: ScanTaskStatus,
        findings: tuple[Finding, ...],
        warnings: tuple[str, ...],
        errors: tuple[str, ...],
        audited_dependencies: int,
        skipped: tuple[str, ...],
        *,
        cancelled: bool = False,
        progress: int = 100,
        summary: str = "",
    ) -> DependencyAuditOutcome:
        now = self._clock()
        stamp = to_db_time(now)
        if status is ScanTaskStatus.COMPLETED:
            final_summary = summary or (
                f"已审计 {audited_dependencies} 个依赖，发现 {len(findings)} 个唯一漏洞。"
                if findings
                else f"已审计 {audited_dependencies} 个依赖，未发现已知漏洞。"
            )
            error_message = ""
            event_type = "dependency_audit_completed"
            decision = "info"
        elif status is ScanTaskStatus.CANCELLED:
            final_summary = f"依赖审计已取消；已保留 {len(findings)} 个结果。"
            error_message = "用户取消审计"
            event_type = "dependency_audit_cancelled"
            decision = "info"
        else:
            final_summary = f"依赖审计失败；已保留 {len(findings)} 个结果。"
            error_message = "；".join(errors) or "依赖审计失败"
            event_type = "dependency_audit_failed"
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
                    final_summary,
                    error_message,
                    1 if cancelled else 0,
                    stamp if cancelled else None,
                    task_id,
                    discovery.project_id,
                ),
            )
            self._audit.record(
                event_type=event_type,
                target=selected.relative_path,
                operation="dependency_audit",
                decision=decision,
                message=f"依赖审计任务 #{task_id} {status.label}",
                details={
                    "task_id": task_id,
                    "dependency_file": selected.relative_path,
                    "audited_dependencies": audited_dependencies,
                    "findings": len(findings),
                    "warnings": list(warnings)[:20],
                    "errors": list(errors)[:20],
                },
                project_id=discovery.project_id,
                task_id=task_id,
                conn=conn,
                created_at=now,
            )
        task = self.get_task(discovery.project_id, task_id)
        stored = self.list_findings(discovery.project_id, task_id=task_id)
        return DependencyAuditOutcome(
            task=task,
            findings=tuple(stored),
            dependency_file=selected.relative_path,
            audited_dependencies=audited_dependencies,
            warnings=tuple(warnings),
            errors=tuple(errors),
        )

    def _save_findings(
        self, project_id: int, task_id: int, findings: Sequence[Finding]
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
                    finding_id=None,
                    created_at=now,
                    updated_at=now,
                )
                cursor = conn.execute(
                    "INSERT INTO findings "
                    "(project_id, task_id, title, category, risk_level, affected_scope, "
                    "description, remediation, status, created_at, updated_at, confidence, "
                    "file_path, line_number, rule_id, scanner_name, scanner_version, "
                    "detected_at, metadata_json, last_seen_at) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        project_id,
                        task_id,
                        item.title,
                        item.category,
                        item.severity.value,
                        item.affected_scope,
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
                saved.append(replace(item, finding_id=int(cursor.lastrowid or 0)))
        return saved

    # ------------------------------------------------------------------ queries
    def get_task(self, project_id: int, task_id: int) -> ScanTask:
        row = self._db.fetch_one(
            "SELECT * FROM scan_tasks WHERE task_id = ? AND project_id = ? "
            "AND task_type = 'dependency_audit'",
            (task_id, project_id),
        )
        if row is None:
            raise NotFoundError("依赖审计任务不存在或不属于当前项目")
        return ScanTask.from_row(row)

    def latest_task(self, project_id: int) -> ScanTask | None:
        row = self._db.fetch_one(
            "SELECT * FROM scan_tasks WHERE project_id = ? "
            "AND task_type = 'dependency_audit' "
            "ORDER BY created_at DESC, task_id DESC LIMIT 1",
            (project_id,),
        )
        return ScanTask.from_row(row) if row else None

    def list_findings(self, project_id: int, task_id: int | None = None) -> list[Finding]:
        if task_id is None:
            rows = self._db.fetch_all(
                "SELECT * FROM findings WHERE project_id = ? AND scanner_name = 'pip-audit' "
                "ORDER BY CASE risk_level "
                "WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 "
                "WHEN 'low' THEN 2 ELSE 1 END DESC, title ASC",
                (project_id,),
            )
        else:
            rows = self._db.fetch_all(
                "SELECT * FROM findings WHERE project_id = ? AND task_id = ? "
                "AND scanner_name = 'pip-audit' ORDER BY CASE risk_level "
                "WHEN 'critical' THEN 5 WHEN 'high' THEN 4 WHEN 'medium' THEN 3 "
                "WHEN 'low' THEN 2 ELSE 1 END DESC, title ASC",
                (project_id, task_id),
            )
        return [Finding.from_row(row) for row in rows]
