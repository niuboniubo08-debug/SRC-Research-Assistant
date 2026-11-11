"""Evidence records attached to a finding inside one project."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.models.enums import EvidenceType
from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class Evidence:
    evidence_id: int
    project_id: int
    finding_id: int
    evidence_type: EvidenceType
    title: str
    description: str
    file_path: str
    file_name: str
    file_hash: str
    captured_at: datetime
    source: str
    created_at: datetime
    project_name: str = ""
    finding_title: str = ""

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Evidence":
        captured_raw = row["captured_at"] if "captured_at" in row.keys() else None
        created_raw = row["created_at"] if "created_at" in row.keys() else None
        return cls(
            evidence_id=int(row["evidence_id"]),
            project_id=int(row["project_id"]),
            finding_id=int(row["finding_id"]) if row["finding_id"] is not None else 0,
            evidence_type=EvidenceType.from_external(
                str(row["evidence_type"]) if "evidence_type" in row.keys() else "other_file"
            ),
            title=(
                str(row["title"] or "")
                if "title" in row.keys()
                else ""
            ),
            description=str(row["description"] or ""),
            file_path=str(row["file_path"] or ""),
            file_name=str(row["file_name"] or ""),
            file_hash=str(row["sha256"] or ""),
            captured_at=(
                from_db_time(str(captured_raw))
                if captured_raw
                else from_db_time(str(created_raw))
            ),
            source=(
                str(row["source"] or "")
                if "source" in row.keys()
                else ""
            ),
            created_at=from_db_time(str(created_raw)) if created_raw else None,
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
    def type_label(self) -> str:
        return self.evidence_type.label

    @property
    def display_title(self) -> str:
        return self.title or self.file_name or self.type_label

    @property
    def short_hash(self) -> str:
        return f"{self.file_hash[:16]}…" if self.file_hash else "—"

    @property
    def has_file(self) -> bool:
        return bool(self.file_path)
