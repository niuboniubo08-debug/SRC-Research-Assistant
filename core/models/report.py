"""Read-only report DTOs for the phase-6 report boundary.

The report pipeline intentionally separates:

* ``ReportRepository``: one read-only SQLite transaction and project-scoped rows;
* ``ReportService``: statistics, data-scope rules, warnings and evidence checks;
* exporters (later phases): consume only ``ReportSnapshot``.

The DTOs are frozen so a generated report cannot mutate its source snapshot.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping

from core.models.authorization import Authorization
from core.models.enums import (
    Confidence,
    EvidenceType,
    FindingStatus,
    ScanTaskStatus,
    ScanTaskType,
    Severity,
)
from core.models.evidence import Evidence
from core.models.finding import Finding
from core.models.project import Project
from core.models.scan_task import ScanTask
from core.models.scope import ScopeAsset
from core.timeutil import ensure_aware_utc


class ReportType(str, Enum):
    VULNERABILITY = "vulnerability"
    EVIDENCE = "evidence"
    PROJECT_SUMMARY = "project_summary"

    @property
    def label(self) -> str:
        return {
            ReportType.VULNERABILITY: "漏洞分析报告",
            ReportType.EVIDENCE: "证据报告",
            ReportType.PROJECT_SUMMARY: "项目综合安全研究报告",
        }[self]

    @classmethod
    def options(cls) -> list[tuple[str, "ReportType"]]:
        return [(item.label, item) for item in cls]


class ReportFormat(str, Enum):
    HTML = "html"
    PDF = "pdf"
    JSON = "json"

    @property
    def label(self) -> str:
        return {
            ReportFormat.HTML: "HTML",
            ReportFormat.PDF: "PDF",
            ReportFormat.JSON: "JSON",
        }[self]

    @property
    def extension(self) -> str:
        return self.value

    @classmethod
    def options(cls) -> list[tuple[str, "ReportFormat"]]:
        return [(item.label, item) for item in cls]


@dataclass(frozen=True, slots=True)
class ReportRequest:
    """A request for report data. Export itself belongs to later phases."""

    project_id: int
    report_type: ReportType
    report_format: ReportFormat
    title: str = ""
    include_evidence_images: bool = False
    include_notes: bool = True
    requested_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.requested_at is not None:
            object.__setattr__(
                self, "requested_at", ensure_aware_utc(self.requested_at)
            )


@dataclass(frozen=True, slots=True)
class ReportFinding:
    finding_id: int
    project_id: int
    task_id: int | None
    title: str
    category: str
    description: str
    severity: Severity
    severity_source: str
    confidence: Confidence
    scanner_name: str
    scanner_version: str
    rule_id: str
    file_path: str
    line_number: int
    recommendation: str
    status: FindingStatus
    manual_notes: str
    detected_at: datetime
    last_seen_at: datetime
    dependency_name: str | None
    dependency_version: str | None
    vulnerability_id: str | None
    fix_versions: tuple[str, ...]
    affected_versions: str | None
    evidence_count: int
    metadata: Mapping[str, Any]
    raw_metadata_omitted: bool = False

    @property
    def severity_label(self) -> str:
        return self.severity.label

    @property
    def status_label(self) -> str:
        return self.status.label

    @property
    def line_display(self) -> str:
        return str(self.line_number) if self.line_number > 0 else "—"


@dataclass(frozen=True, slots=True)
class ReportEvidence:
    evidence_id: int
    project_id: int
    finding_id: int
    finding_title: str
    evidence_type: EvidenceType
    title: str
    description: str
    file_name: str
    source: str
    file_path: str
    managed_path: str | None
    file_hash: str
    captured_at: datetime
    created_at: datetime
    file_exists: bool | None = None
    hash_matches: bool | None = None
    file_status_note: str = ""

    @property
    def type_label(self) -> str:
        return self.evidence_type.label

    @property
    def display_title(self) -> str:
        return self.title or self.file_name or self.type_label


@dataclass(frozen=True, slots=True)
class ReportTaskSummary:
    task_id: int
    project_id: int
    task_type: ScanTaskType
    target: str
    status: ScanTaskStatus
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime
    result_summary: str
    error_message: str
    progress: int
    scanners: tuple[str, ...]
    current_scanner: str

    @property
    def type_label(self) -> str:
        return self.task_type.label

    @property
    def status_label(self) -> str:
        return self.status.label


@dataclass(frozen=True, slots=True)
class ReportAuthorizationSummary:
    as_of: datetime
    total_count: int
    effective_count: int
    confirmed_count: int
    expired_count: int
    pending_count: int
    revoked_count: int
    scope_asset_count: int
    active_scope_asset_count: int
    historical_scan_authorization_available: bool = False
    note: str = ""

    @property
    def has_effective_authorization(self) -> bool:
        return self.effective_count > 0


@dataclass(frozen=True, slots=True)
class ReportStats:
    task_count: int = 0
    task_status_counts: Mapping[str, int] = field(default_factory=dict)
    task_scanner_counts: Mapping[str, int] = field(default_factory=dict)
    finding_count: int = 0
    severity_counts: Mapping[str, int] = field(default_factory=dict)
    scanner_counts: Mapping[str, int] = field(default_factory=dict)
    finding_status_counts: Mapping[str, int] = field(default_factory=dict)
    dependency_finding_count: int = 0
    evidence_count: int = 0
    evidence_type_counts: Mapping[str, int] = field(default_factory=dict)
    file_evidence_count: int = 0
    missing_evidence_file_count: int = 0
    hash_mismatch_count: int = 0

    def __post_init__(self) -> None:
        for name in (
            "task_status_counts",
            "task_scanner_counts",
            "severity_counts",
            "scanner_counts",
            "finding_status_counts",
            "evidence_type_counts",
        ):
            value = getattr(self, name)
            if not isinstance(value, MappingProxyType):
                object.__setattr__(self, name, MappingProxyType(dict(value)))


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    snapshot_id: str
    report_type: ReportType
    project: Project
    authorization: ReportAuthorizationSummary
    tasks: tuple[ReportTaskSummary, ...]
    findings: tuple[ReportFinding, ...]
    evidence: tuple[ReportEvidence, ...]
    stats: ReportStats | None
    generated_at: datetime
    schema_version: int
    data_scope: tuple[str, ...]
    warnings: tuple[str, ...]
    known_limitations: tuple[str, ...]

    @property
    def project_id(self) -> int:
        return self.project.project_id

    @property
    def finding_count(self) -> int:
        return len(self.findings)

    @property
    def evidence_count(self) -> int:
        return len(self.evidence)


@dataclass(frozen=True, slots=True)
class ReportArtifact:
    """Generic future result structure; no file is written in phase B."""

    report_type: ReportType
    report_format: ReportFormat
    project_id: int
    title: str
    generated_at: datetime
    snapshot_id: str
    path: str | None = None
    sha256: str | None = None
    warnings: tuple[str, ...] = ()
