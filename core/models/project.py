"""Project domain model."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.models.enums import ProjectStatus, ProjectType
from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class Project:
    project_id: int
    project_name: str
    project_type: ProjectType
    description: str
    local_path: str
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "Project":
        return cls(
            project_id=int(row["project_id"]),
            project_name=str(row["project_name"]),
            project_type=ProjectType(str(row["project_type"])),
            description=str(row["description"] or ""),
            local_path=str(row["local_path"] or ""),
            status=ProjectStatus(str(row["status"])),
            created_at=from_db_time(str(row["created_at"])),
            updated_at=from_db_time(str(row["updated_at"])),
        )

    @property
    def type_label(self) -> str:
        return self.project_type.label

    @property
    def status_label(self) -> str:
        return self.status.label
