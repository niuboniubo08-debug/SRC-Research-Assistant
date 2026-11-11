"""Business-level report data organization for phase 6.

This module deliberately performs no HTML/PDF/JSON rendering.  It builds a
single, project-scoped snapshot that later exporters must consume unchanged.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from types import MappingProxyType

from core.errors import ValidationError
from core.models.enums import (
    AuthStatus,
    EvidenceType,
    FindingStatus,
    ScanTaskStatus,
    Severity,
)
from core.models.report import (
    ReportArtifact,
    ReportEvidence,
    ReportFormat,
    ReportRequest,
    ReportSnapshot,
    ReportStats,
    ReportType,
)
from core.timeutil import ensure_aware_utc, utc_now
from services.evidence_service import sha256_file

_REPORT_SCOPES: dict[ReportType, tuple[str, ...]] = {
    ReportType.VULNERABILITY: (
        "project",
        "current_authorization",
        "scan_tasks",
        "findings",
        "finding_stats",
    ),
    ReportType.EVIDENCE: (
        "project",
        "current_authorization",
        "scan_tasks",
        "evidence",
        "evidence_stats",
        "linked_findings",
    ),
    ReportType.PROJECT_SUMMARY: (
        "project",
        "current_authorization",
        "scan_tasks",
        "findings",
        "evidence",
        "finding_stats",
        "evidence_stats",
    ),
}

_KNOWN_LIMITATIONS = (
    "Semgrep 1.183.0 在当前 Windows 会话因 CA 存储初始化失败，报告中出现的 "
    "Semgrep 记录只能来自数据库已有数据，不能视为本次真实 Semgrep 审计。",
    "pip-audit 不提供 CVSS/severity 和精确 affected range；现有 severity_source "
    "和当前版本信息按数据库已有数据展示，不补造。",
    "当前授权摘要按报告生成时刻计算，不等于历史扫描发生时的授权状态；"
    "数据库没有保存扫描时授权快照。",
    "未实现跨扫描 Finding 逻辑去重；首次/最近时间按每条 Finding 记录展示。",
    "数据库没有统一的“真实扫描/测试夹具/模拟数据”来源标记；报告按已有记录"
    "表达，不会自动把夹具数据标记为真实扫描。",
    "报告数据来源为本地 SQLite 快照及项目受管证据文件校验；不访问远程目标。",
)


class ReportService:
    def __init__(
        self,
        database,
        repository,
        *,
        evidence_root: str | Path | None = None,
        clock=utc_now,
    ) -> None:
        self._db = database
        self._repository = repository
        self._root = (
            Path(evidence_root).expanduser().resolve()
            if evidence_root is not None
            else None
        )
        self._clock = clock

    def get_snapshot(
        self, project_id: int, report_type: ReportType | str
    ) -> ReportSnapshot:
        kind = self._coerce_type(report_type)
        generated_at = ensure_aware_utc(self._clock())
        raw = self._repository.load_snapshot(
            int(project_id), kind, generated_at=generated_at
        )
        return self._finalize(raw)

    def get_snapshot_for_request(self, request: ReportRequest) -> ReportSnapshot:
        if not isinstance(request, ReportRequest):
            raise ValidationError("报告请求类型无效")
        self._coerce_format(request.report_format)
        return self.get_snapshot(request.project_id, request.report_type)

    def _finalize(self, snapshot: ReportSnapshot) -> ReportSnapshot:
        evidence, file_warnings = self._annotate_evidence(snapshot)
        stats = self._build_stats(snapshot, evidence)
        warnings = self._build_warnings(snapshot, stats, file_warnings)
        return replace(
            snapshot,
            evidence=evidence,
            stats=stats,
            data_scope=_REPORT_SCOPES[snapshot.report_type],
            warnings=tuple(warnings),
            known_limitations=_KNOWN_LIMITATIONS,
        )

    def _annotate_evidence(
        self, snapshot: ReportSnapshot
    ) -> tuple[tuple[ReportEvidence, ...], list[str]]:
        warnings: list[str] = []
        if self._root is None:
            return snapshot.evidence, warnings
        project_root = (self._root / f"project_{snapshot.project.project_id}").resolve()
        annotated: list[ReportEvidence] = []
        for item in snapshot.evidence:
            if not item.file_path:
                annotated.append(item)
                continue
            path = Path(item.file_path).expanduser()
            if not path.is_absolute():
                annotated.append(
                    replace(
                        item,
                        managed_path=None,
                        file_exists=False,
                        hash_matches=None,
                        file_status_note="数据库中的证据路径不是绝对路径，未读取文件。",
                    )
                )
                warnings.append(f"证据 #{item.evidence_id} 的路径不是绝对路径。")
                continue
            if path.is_symlink():
                annotated.append(
                    replace(
                        item,
                        managed_path=None,
                        file_exists=False,
                        hash_matches=None,
                        file_status_note="证据路径是符号链接，未读取文件。",
                    )
                )
                warnings.append(f"证据 #{item.evidence_id} 是符号链接，未读取。")
                continue
            try:
                resolved = path.resolve(strict=False)
                relative = resolved.relative_to(project_root)
            except (OSError, ValueError):
                annotated.append(
                    replace(
                        item,
                        managed_path=None,
                        file_exists=False,
                        hash_matches=None,
                        file_status_note="证据文件不在当前项目受管证据目录内。",
                    )
                )
                warnings.append(
                    f"证据 #{item.evidence_id} 不在当前项目受管证据目录内，未读取。"
                )
                continue
            managed = (Path(f"project_{snapshot.project.project_id}") / relative).as_posix()
            if not resolved.is_file():
                annotated.append(
                    replace(
                        item,
                        managed_path=managed,
                        file_exists=False,
                        hash_matches=None,
                        file_status_note="证据文件不存在。",
                    )
                )
                warnings.append(f"证据 #{item.evidence_id} 的受管文件不存在。")
                continue
            hash_matches: bool | None = None
            note = ""
            if item.file_hash:
                try:
                    actual = sha256_file(resolved)
                    hash_matches = actual.lower() == item.file_hash.lower()
                    if not hash_matches:
                        note = "证据文件 SHA-256 与数据库记录不一致。"
                        warnings.append(
                            f"证据 #{item.evidence_id} 的 SHA-256 不一致。"
                        )
                except OSError:
                    note = "证据文件存在但无法读取以校验哈希。"
                    warnings.append(
                        f"证据 #{item.evidence_id} 无法读取以校验 SHA-256。"
                    )
            annotated.append(
                replace(
                    item,
                    managed_path=managed,
                    file_exists=True,
                    hash_matches=hash_matches,
                    file_status_note=note,
                )
            )
        return tuple(annotated), warnings

    def _build_stats(
        self,
        snapshot: ReportSnapshot,
        evidence: tuple[ReportEvidence, ...],
    ) -> ReportStats:
        task_status_counts = {status.value: 0 for status in ScanTaskStatus}
        task_scanner_counts: dict[str, int] = {}
        for task in snapshot.tasks:
            task_status_counts[task.status.value] += 1
            for scanner in task.scanners:
                task_scanner_counts[scanner] = task_scanner_counts.get(scanner, 0) + 1

        severity_counts = {severity.value: 0 for severity in Severity}
        scanner_counts: dict[str, int] = {}
        status_counts = {status.value: 0 for status in FindingStatus}
        dependency_count = 0
        for finding in snapshot.findings:
            severity_counts[finding.severity.value] += 1
            scanner_counts[finding.scanner_name or "unknown"] = (
                scanner_counts.get(finding.scanner_name or "unknown", 0) + 1
            )
            status_counts[finding.status.value] += 1
            if finding.dependency_name:
                dependency_count += 1

        evidence_type_counts = {kind.value: 0 for kind in EvidenceType}
        for item in evidence:
            evidence_type_counts[item.evidence_type.value] += 1

        return ReportStats(
            task_count=len(snapshot.tasks),
            task_status_counts=task_status_counts,
            task_scanner_counts=task_scanner_counts,
            finding_count=len(snapshot.findings),
            severity_counts=severity_counts,
            scanner_counts=scanner_counts,
            finding_status_counts=status_counts,
            dependency_finding_count=dependency_count,
            evidence_count=len(evidence),
            evidence_type_counts=evidence_type_counts,
            file_evidence_count=sum(1 for item in evidence if item.file_path),
            missing_evidence_file_count=sum(
                1 for item in evidence if item.file_path and item.file_exists is False
            ),
            hash_mismatch_count=sum(
                1 for item in evidence if item.hash_matches is False
            ),
        )

    def _build_warnings(
        self,
        snapshot: ReportSnapshot,
        stats: ReportStats,
        file_warnings: list[str],
    ) -> list[str]:
        warnings: list[str] = []
        if stats.task_count == 0:
            warnings.append("项目没有扫描任务；不能据此推断扫描通过。")
        if stats.finding_count == 0:
            warnings.append("项目没有 Finding；不能据此推断不存在漏洞。")
        if stats.evidence_count == 0:
            warnings.append("项目没有 Evidence 记录。")
        if snapshot.authorization.total_count == 0:
            warnings.append("项目没有授权记录；报告不能作为授权完成证明。")
        elif snapshot.authorization.effective_count == 0:
            warnings.append("当前没有有效授权记录；报告只展示已有本地数据。")
        failed_tasks = sum(
            1
            for task in snapshot.tasks
            if task.status in {ScanTaskStatus.FAILED, ScanTaskStatus.CANCELLED}
        )
        if failed_tasks:
            warnings.append(f"存在 {failed_tasks} 个失败或取消的扫描任务。")
        if self._root is None:
            warnings.append("未配置证据根目录，未验证证据文件存在性和 SHA-256。")
        if stats.missing_evidence_file_count:
            warnings.append(
                f"{stats.missing_evidence_file_count} 份证据文件缺失或不可读。"
            )
        if stats.hash_mismatch_count:
            warnings.append(
                f"{stats.hash_mismatch_count} 份证据文件的 SHA-256 与记录不一致。"
            )
        omitted = sum(1 for item in snapshot.findings if item.raw_metadata_omitted)
        if omitted:
            warnings.append(
                f"{omitted} 条 Finding 的原始 metadata 仅保留安全白名单字段。"
            )
        warnings.extend(file_warnings)
        return warnings

    @staticmethod
    def _coerce_type(value: ReportType | str) -> ReportType:
        try:
            return value if isinstance(value, ReportType) else ReportType(str(value))
        except ValueError as exc:
            raise ValidationError("报告类型无效") from exc

    @staticmethod
    def _coerce_format(value: ReportFormat | str) -> ReportFormat:
        try:
            return value if isinstance(value, ReportFormat) else ReportFormat(str(value))
        except ValueError as exc:
            raise ValidationError("报告格式无效") from exc

    @staticmethod
    def artifact_stub(
        request: ReportRequest, snapshot: ReportSnapshot
    ) -> ReportArtifact:
        """Return a metadata-only result placeholder; no file is written here."""

        return ReportArtifact(
            report_type=request.report_type,
            report_format=request.report_format,
            project_id=request.project_id,
            title=request.title,
            generated_at=snapshot.generated_at,
            snapshot_id=snapshot.snapshot_id,
            warnings=snapshot.warnings,
        )
