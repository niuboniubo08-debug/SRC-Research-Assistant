"""Unified source-audit finding model.

Bandit and Semgrep results are converted into this model before persistence;
raw tool JSON is never stored as the business result.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.models.enums import Confidence, FindingStatus, Severity
from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class Finding:
    title: str
    category: str
    severity: Severity
    confidence: Confidence
    description: str
    file_path: str
    line_number: int
    rule_id: str
    recommendation: str
    scanner_name: str
    scanner_version: str
    detected_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
    project_id: int | None = None
    task_id: int | None = None
    affected_scope: str = ""
    status: str = "open"
    manual_notes: str = ""
    status_changed_at: datetime | None = None
    last_seen_at: datetime | None = None
    project_name: str = ""
    evidence_count: int = 0
    finding_id: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Finding":
        detected_raw = row["detected_at"] if "detected_at" in row.keys() else None
        created_raw = row["created_at"] if "created_at" in row.keys() else None
        detected_at = (
            from_db_time(str(detected_raw))
            if detected_raw
            else from_db_time(str(created_raw))
        )
        line_value = row["line_number"] if "line_number" in row.keys() else None
        confidence_raw = row["confidence"] if "confidence" in row.keys() else "unknown"
        metadata: dict[str, Any] = {}
        if "metadata_json" in row.keys() and row["metadata_json"]:
            try:
                parsed = json.loads(str(row["metadata_json"]))
                if isinstance(parsed, dict):
                    metadata = parsed
            except (TypeError, ValueError):
                metadata = {}
        return cls(
            finding_id=int(row["finding_id"]),
            project_id=int(row["project_id"]),
            task_id=int(row["task_id"]) if row["task_id"] is not None else None,
            title=str(row["title"]),
            category=str(row["category"] or ""),
            severity=Severity(str(row["risk_level"])),
            confidence=Confidence.from_external(str(confidence_raw or "unknown")),
            description=str(row["description"] or ""),
            file_path=str(row["file_path"] or ""),
            line_number=int(line_value or 0),
            rule_id=str(row["rule_id"] or ""),
            recommendation=str(row["remediation"] or ""),
            scanner_name=str(row["scanner_name"] or ""),
            scanner_version=str(row["scanner_version"] or ""),
            detected_at=detected_at,
            metadata=metadata,
            affected_scope=str(row["affected_scope"] or ""),
            status=str(row["status"] or "open"),
            manual_notes=(
                str(row["manual_notes"] or "")
                if "manual_notes" in row.keys()
                else ""
            ),
            status_changed_at=(
                from_db_time(str(row["status_changed_at"]))
                if "status_changed_at" in row.keys() and row["status_changed_at"]
                else None
            ),
            last_seen_at=(
                from_db_time(str(row["last_seen_at"]))
                if "last_seen_at" in row.keys() and row["last_seen_at"]
                else None
            ),
            project_name=(
                str(row["project_name"] or "")
                if "project_name" in row.keys()
                else ""
            ),
            evidence_count=(
                int(row["evidence_count"] or 0)
                if "evidence_count" in row.keys()
                else 0
            ),
            created_at=from_db_time(str(row["created_at"])) if row["created_at"] else None,
            updated_at=from_db_time(str(row["updated_at"])) if row["updated_at"] else None,
        )

    @property
    def risk_level(self) -> str:
        """Database-compatible alias."""

        return self.severity.value

    @property
    def severity_label(self) -> str:
        return self.severity.label

    @property
    def status_enum(self) -> FindingStatus:
        return FindingStatus.from_external(self.status)

    @property
    def status_label(self) -> str:
        return self.status_enum.label

    @property
    def first_seen(self) -> datetime:
        return self.detected_at

    @property
    def last_seen(self) -> datetime:
        return self.last_seen_at or self.detected_at

    @property
    def confidence_label(self) -> str:
        return self.confidence.label

    @property
    def line_display(self) -> str:
        return str(self.line_number) if self.line_number > 0 else "—"

    @property
    def scanner_label(self) -> str:
        names = {"bandit": "Bandit", "semgrep": "Semgrep", "pip-audit": "pip-audit"}
        return names.get(self.scanner_name, self.scanner_name or "未知")


@dataclass(frozen=True, slots=True)
class FindingStatusHistory:
    history_id: int
    project_id: int
    finding_id: int
    from_status: str
    to_status: str
    note: str
    changed_by: str
    changed_at: datetime
    project_name: str = ""
    finding_title: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "FindingStatusHistory":
        return cls(
            history_id=int(row["history_id"]),
            project_id=int(row["project_id"]),
            finding_id=int(row["finding_id"]),
            from_status=str(row["from_status"] or "open"),
            to_status=str(row["to_status"] or "open"),
            note=str(row["note"] or ""),
            changed_by=str(row["changed_by"] or "local_user"),
            changed_at=from_db_time(str(row["changed_at"])),
            project_name=(
                str(row["project_name"] or "")
                if "project_name" in row.keys()
                else ""
            ),
            finding_title=(
                str(row["finding_title"] or "")
                if "finding_title" in row.keys()
                else ""
            ),
        )

    @property
    def from_label(self) -> str:
        return FindingStatus.from_external(self.from_status).label

    @property
    def to_label(self) -> str:
        return FindingStatus.from_external(self.to_status).label
