"""System audit log model."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime

from core.timeutil import from_db_time


@dataclass(frozen=True, slots=True)
class ScanLog:
    log_id: int
    project_id: int | None
    task_id: int | None
    event_type: str
    target: str
    operation: str
    decision: str
    message: str
    details_json: str
    created_at: datetime

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "ScanLog":
        return cls(
            log_id=int(row["log_id"]),
            project_id=int(row["project_id"]) if row["project_id"] is not None else None,
            task_id=int(row["task_id"]) if row["task_id"] is not None else None,
            event_type=str(row["event_type"]),
            target=str(row["target"] or ""),
            operation=str(row["operation"] or ""),
            decision=str(row["decision"] or "info"),
            message=str(row["message"] or ""),
            details_json=str(row["details_json"] or "{}"),
            created_at=from_db_time(str(row["created_at"])),
        )
